import json
import datetime
import sys


def generate_report():
    """
    Generates an HTML performance report by comparing PR and Baseline JSON data.
    PQI Score is calculated based on p95 latency.
    """

    # --- 1. Load Data ---
    try:
        # baseline_data is loaded ONLY from 'baseline_report.json'
        with open('baseline_report.json', 'r') as f:
            baseline_data = json.load(f)
        # pr_data is loaded ONLY from 'pr_report.json'
        with open('pr_report.json', 'r') as f:
            pr_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: Required file not found. Make sure '{e.filename}' is in the same directory.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON file. Check for syntax errors. {e}")
        sys.exit(1)

    # baseline_summaries is derived ONLY from baseline_data (from baseline_report.json)
    baseline_summaries = baseline_data.get('aggregate', {}).get('summaries', {})
    # pr_summaries is derived ONLY from pr_data (from pr_report.json)
    pr_summaries = pr_data.get('aggregate', {}).get('summaries', {})

    # --- 2. Process Endpoints ---

    endpoint_results = []
    total_endpoints = 0
    passing_endpoints = 0
    failing_endpoints = 0

    # This is the "Penalty Factor (0.5)" from your image
    penalty_factor = 0.5
    api_prefix = "plugins.metrics-by-endpoint.response_time."

    # Iterate over all endpoints found in the PR report (pr_summaries)
    for key, pr_stats in pr_summaries.items():
        # Check if it's an endpoint metric
        if not key.startswith(api_prefix):
            continue

        api_path = key.replace(api_prefix, "")

        # Filter for *only* application APIs (as requested)
        if not api_path.startswith('/api/'):
            continue

        total_endpoints += 1

        # Get corresponding baseline stats from baseline_summaries (which is from baseline_report.json)
        baseline_stats = baseline_summaries.get(key)

        # Get all relevant PR metrics from pr_stats (which is from pr_report.json)
        pr_p95 = pr_stats.get('p95', 0)
        pr_avg = pr_stats.get('mean', 0)
        pr_count = pr_stats.get('count', 0)
        pr_min = pr_stats.get('min', 0)
        pr_max = pr_stats.get('max', 0)
        pr_p99 = pr_stats.get('p99', 0)

        if not baseline_stats:
            # This endpoint key was not found in baseline_summaries
            # Set baseline_p95 to 0.0 as there is no base data to compare
            baseline_p95 = 0.0
            pqi_score = 100.0  # No regression possible, perfect score

            # For new endpoints, judge status on an absolute threshold
            if pr_p95 > 50:
                status = "FAIL"
            elif pr_p95 > 20:
                status = "WARN"
            else:
                status = "PASS"
        else:
            # This is an existing endpoint, calculate PQI
            # Get baseline_p95 ONLY from baseline_stats (which is from baseline_report.json)
            baseline_p95 = baseline_stats.get('p95', 0)

            # Calculate latency increase based on P95
            latency_increase = pr_p95 - baseline_p95 # This uses the separate pr_p95 and baseline_p95

            # Penalty only applies to *increases*
            penalty = max(0, latency_increase) * penalty_factor

            # Final PQI score
            pqi_score = 100.0 - penalty

            # Determine status based on the PQI score
            if pqi_score < 90:
                status = "FAIL"
            elif pqi_score < 95:
                status = "WARN"
            else:
                status = "PASS"

        # Update summary counters
        if status == "PASS":
            passing_endpoints += 1
        elif status in ["FAIL", "WARN"]:
            failing_endpoints += 1

        # Store all calculated data
        endpoint_results.append({
            'path': api_path,
            'p95_latest': pr_p95,     # This value comes from pr_report.json
            'p95_base': baseline_p95,  # This value comes from baseline_report.json (or 0.0 if new)
            'pqi_score': pqi_score,
            'status': status,
            'avg_latency': pr_avg,
            'count': pr_count,
            'min_latency': pr_min,
            'max_latency': pr_max,
            'p99_latency': pr_p99
        })

    # --- 3. Calculate Summary Metrics ---

    if total_endpoints > 0:
        success_rate = (passing_endpoints / total_endpoints) * 100
    else:
        success_rate = 100.0  # No APIs found, so 100% "passing"

    with open('score_output.json', 'w') as score_file:
        json.dump({'success_rate': success_rate}, score_file, indent=4)

    # Get overall latency from the aggregate block
    if total_endpoints > 0:
        overall_avg_latency = sum(r['avg_latency'] for r in endpoint_results) / total_endpoints
    else:
        overall_avg_latency = 0.0 # No APIs found, so overall average is 0
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- 4. Prepare Dynamic HTML Components ---

    # --- Prepare "Score Calculation Breakdown" Table Rows ---
    table_rows_html = ""
    status_colors = {
        "PASS": "bg-green-100 text-green-700",
        "WARN": "bg-yellow-100 text-yellow-700",
        "FAIL": "bg-red-100 text-red-700"
    }

    if not endpoint_results:
        table_rows_html = """
        <tr>
            <td colspan="5" class="p-4 text-center text-gray-500">
                No API endpoints (starting with '/api/') found in the report.
            </td>
        </tr>
        """

    for r in endpoint_results:
        color_class = status_colors.get(r['status'], "bg-gray-100 text-gray-700")
        table_rows_html += f"""
        <tr class="border-b border-gray-100 hover:bg-gray-50 transition duration-150">
            <td class="p-4 text-sm font-medium text-gray-800 break-all">{r['path']}</td>
            <td class="p-4 text-sm text-gray-700">{r['p95_latest']:.2f} ms</td>
            <td class="p-4 text-sm text-gray-700">{r['p95_base']:.2f} ms</td>
            <td class="p-4 text-sm font-bold {color_class.replace('bg', 'text')}">{r['pqi_score']:.2f}</td>
            <td class="p-4">
                <span class="px-3 py-1 text-xs rounded-full {color_class} font-medium">
                    {r['status']}
                </span>
            </td>
        </tr>
        """

    # --- Prepare "Detailed Latency Metrics" Accordion Rows ---
    accordion_rows_html = ""
    if not endpoint_results:
        accordion_rows_html = """
        <tr>
            <td colspan="6" class="p-4 text-center text-gray-500">
                No API endpoints (starting with '/api/') found in the report.
            </td>
        </tr>
        """

    for r in endpoint_results:
        accordion_rows_html += f"""
        <tr class="border-b border-gray-100 hover:bg-gray-50 transition duration-150">
            <td class="p-4 text-sm font-medium text-gray-800 break-all">{r['path']}</td>
            <td class="p-4 text-sm text-gray-700">{r['count']}</td>
            <td class="p-4 text-sm text-gray-700">{r['min_latency']:.2f} ms</td>
            <td class="p-4 text-sm text-gray-700">{r['max_latency']:.2f} ms</td>
            <td class="p-4 text-sm text-gray-700">{r['avg_latency']:.2f} ms</td>
            <td class="p-4 text-sm text-gray-700">{r['p99_latency']:.2f} ms</td>
        </tr>
        """

    # --- Prepare Chart Data ---
    chart_paths = [r['path'] for r in endpoint_results]
    chart_p95_pr = [r['p95_latest'] for r in endpoint_results]   # From pr_report.json
    chart_p95_base = [r['p95_base'] for r in endpoint_results] # From baseline_report.json

    # Convert Python lists to JS-compatible JSON strings
    chart_paths_js = json.dumps(chart_paths)
    chart_p95_pr_js = json.dumps(chart_p95_pr)
    chart_p95_base_js = json.dumps(chart_p95_base)

    # --- 5. Assemble the Final HTML ---

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Performance PQI Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
    <style>
        /* Custom font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
        /* Specific styling for the summary box numbers */
        .metric-value {{ font-size: 2.5rem; font-weight: 700; }}
        /* Style for the accordion */
        details > summary {{ list-style: none; cursor: pointer; }}
        details > summary::-webkit-details-marker {{ display: none; }}
        details[open] summary .arrow-down {{ display: none; }}
        details:not([open]) summary .arrow-up {{ display: none; }}
    </style>
</head>
<body class="bg-gray-50 text-gray-800">

    <div class="max-w-7xl mx-auto p-6 lg:p-10">

        <header class="mb-10 p-6 bg-white shadow-xl rounded-xl">
            <h1 class="text-4xl font-extrabold text-indigo-700">API Performance PQI Report</h1>
            <p class="text-gray-500 mt-2">Comparison of PR against Baseline</p>
            <p class="text-gray-500 mt-1">Generated on {generation_time}</p>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">

            <div class="bg-white p-6 rounded-xl shadow-lg border-l-4 border-indigo-500">
                <p class="text-sm text-gray-500 font-semibold">Success Rate (by PQI)</p>
                <p class="metric-value text-indigo-700 mt-1">{success_rate:.1f}%</p>
                <span class="text-xs text-gray-400">Total API Endpoints: {total_endpoints}</span>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-lg border-l-4 border-blue-500">
                <p class="text-sm text-gray-500 font-semibold">Overall Avg Latency (PR)</p>
                <p class="metric-value text-blue-700 mt-1">{overall_avg_latency:.2f} ms</p>
                <span class="text-xs text-gray-400">Mean latency across all requests</span>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-lg border-l-4 border-green-500">
                <p class="text-sm text-gray-500 font-semibold">Passing Endpoints</p>
                <p class="metric-value text-green-700 mt-1">{passing_endpoints}</p>
                <span class="text-xs text-gray-400">Status: PASS (PQI >= 95)</span>
            </div>

            <div class="bg-white p-6 rounded-xl shadow-lg border-l-4 border-red-500">
                <p class="text-sm text-gray-500 font-semibold">Failing/Warning Endpoints</p>
                <p class="metric-value text-red-700 mt-1">{failing_endpoints}</p>
                <span class="text-xs text-gray-400">Status: FAIL or WARN (PQI < 95)</span>
            </div>

        </div>

        <section class="mb-12">
            <h2 class="text-2xl font-bold text-gray-700 mb-6">p95 Latency: Baseline vs. PR</h2>
            <div class="bg-white p-6 rounded-xl shadow-lg">
                <h3 class="text-lg font-semibold mb-4 text-gray-600">95th Percentile Response Time (ms)</h3>
                <canvas id="p95LatencyChart"></canvas>
            </div>
        </section>


        <section class="mb-12">
            <h2 class="text-2xl font-bold text-gray-700 mb-6">Score Calculation Breakdown</h2>
            <div class="bg-white rounded-xl shadow-lg overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-indigo-50">
                        <tr>
                            <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                                API Path
                            </th>
                            <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                                p95 Latency (PR)
                            </th>
                            <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                                p95 Latency (Base)
                            </th>
                            <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                                PQI Score
                            </th>
                            <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                                Status
                            </th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </section>

        <section class="mb-12">
            <details class="bg-white rounded-xl shadow-lg overflow-hidden">
                <summary class="p-4 flex justify-between items-center text-xl font-bold text-gray-700 bg-gray-50 hover:bg-gray-100">
                    Detailed Latency Metrics (Advanced)
                    <span class="text-indigo-600">
                        <svg class="w-6 h-6 arrow-down" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        <svg class="w-6 h-6 arrow-up" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path></svg>
                    </span>
                </summary>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-indigo-50">
                            <tr>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">API Path</th>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Count</th>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Min Latency</th>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Max Latency</th>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Average Latency</th>
                                <th scope="col" class="p-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">p99 Latency</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                            {accordion_rows_html}
                        </tbody>
                    </table>
                </div>
            </details>
        </section>

        <section>
            <h2 class="text-2xl font-bold text-gray-700 mb-6">Score Calculation Scheme</h2>
            <div class="bg-white p-6 rounded-xl shadow-lg text-gray-700 space-y-3">
                <h3 class="text-xl font-semibold text-indigo-700">Performance Quality Index (PQI)</h3>
                <p>The PQI Score is a metric calculated on a scale of 0-100.</p>
                <p>The score is calculated for each API endpoint using its <strong>95th Percentile (p95)</strong> latency.</p>

                <code class="block bg-gray-100 p-4 rounded-lg text-sm font-mono space-y-2">
                   <p>Latency_Increase = PR_p95_Latency - Baseline_p95_Latency</p>
                   <p>Penalty = max(0, Latency_Increase) * 0.5</p>
                   <p><strong>Final_PQI_Score = 100 - Penalty</strong></p>
                </code>

                <ul class="list-disc list-inside space-y-1 text-sm">
                    <li>A <strong>Penalty Factor</strong> of <strong>0.5</strong> is used (as per the requirement).</li>
                    <li>The passing threshold for the PQI score is <strong>95.</li>

                </ul>
            </div>
        </section>

    </div>

    <script>
        const paths = {chart_paths_js};
        const p95PrValues = {chart_p95_pr_js};
        const p95BaseValues = {chart_p95_base_js};

        // --- Chart Helper Function ---
        function createChart(chartId, labels, baseData, prData) {{
            const ctx = document.getElementById(chartId).getContext('2d');

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Baseline p95',
                            data: baseData,
                            backgroundColor: '#9099ab', // Gray-500
                            barThickness: 20,
                            borderRadius: 4,
                        }},
                        {{
                            label: 'PR p95',
                            data: prData,
                            backgroundColor: '#4b4885', // Indigo-600
                            barThickness: 20,
                            borderRadius: 4,
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    indexAxis: 'x', // Vertical bar chart
                    scales: {{
                        x: {{
                            title: {{
                                display: false,
                                text: 'Endpoint'
                            }}
                        }},
                        y: {{
                            title: {{
                                display: true,
                                text: 'Latency (ms)'
                            }},
                            beginAtZero: true
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true // Show legend to differentiate bars
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.dataset.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    if (context.parsed.y !== null) {{
                                        label += context.parsed.y.toFixed(2) + ' ms';
                                    }}
                                    return label;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // --- Render Charts ---
        if (paths.length > 0) {{
            createChart('p95LatencyChart', paths, p95BaseValues, p95PrValues); 
        }}

    </script>

</body>
</html>
"""
    return html_template


def save_report(html_content, filename="pqi_performance_report.html"):
    """
    Saves the generated HTML content to a file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ Performance report saved as: {filename}")


# --- Main execution ---
if __name__ == "__main__":
    try:
        report_html = generate_report()
        save_report(report_html)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)