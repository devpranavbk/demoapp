import lighthouse from "lighthouse";
import chromeLauncher from "chrome-launcher";
import fs from "fs";

export async function runLighthouse(page) {
    console.log(`💡 Running Lighthouse for page: ${page}`);

    let url = "";
    if (page === "login") {
        url = "https://demoapp-ashen.vercel.app/login/";
    } else if (page === "home") {
        url = "https://demoapp-ashen.vercel.app/";
    } else {
        console.log("❌ Invalid PAGE for Lighthouse");
        return null;
    }

    const chrome = await chromeLauncher.launch({ chromeFlags: ["--headless"] });
    const options = {
        logLevel: "info",
        output: "json",
        onlyCategories: ["performance"],
        port: chrome.port
    };

    try {
        const runnerResult = await lighthouse(url, options);

        const reportJson = runnerResult.report;
        const lightHouseOutputPath = `lighthouse/lh-report-${page}.json`;

        if (!fs.existsSync("lighthouse")) fs.mkdirSync("lighthouse");

        fs.writeFileSync(lightHouseOutputPath, reportJson);

        console.log(`📄 Lighthouse report saved → ${lightHouseOutputPath}`);

        return JSON.parse(reportJson);
    } catch (err) {
        console.log("❌ Lighthouse Failed:", err);
        return null;
    } finally {
        await chrome.kill();
    }
}
