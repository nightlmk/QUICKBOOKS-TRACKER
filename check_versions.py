import json
import urllib.request
from datetime import datetime

# Only 2022-2024 US Windows versions (no Mac, no POS)
versions = [
    ("QuickBooks Pro 2024",              "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2024/Latest/QuickBooksProSub2024.exe"),
    ("QuickBooks Pro 2023",              "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2023/Latest/QuickBooksProSub2023.exe"),
    ("QuickBooks Pro 2022",              "https://dlm2.download.intuit.com/akdlm/SBD/QuickBooks/2022/Latest/QuickBooksProSub2022.exe"),
    ("QuickBooks Premier 2024",          "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2024/Latest/QuickBooksPremierSub2024.exe"),
    ("QuickBooks Premier 2023",          "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2023/Latest/QuickBooksPremierSub2023.exe"),
    ("QuickBooks Premier 2022",          "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2022/Latest/QuickBooksPremierSub2022.exe"),
    ("QuickBooks Accountant 2024",       "https://dlm2.download.intuit.com/akdlm/SBD/QuickBooks/2024/LatestAcc/QuickBooksPremier2024.exe"),
    ("QuickBooks Accountant 2023",       "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2023/Latest/QuickBooksPremier2023.exe"),
    ("QuickBooks Accountant 2022",       "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2022/Latest/QuickBooksPremier2022.exe"),
    ("QuickBooks Enterprise 24",         "https://dlm2.download.intuit.com/akdlm/SBD/QuickBooks/2024/Latest/QuickBooksEnterprise24.exe"),
    ("QuickBooks Enterprise Acct 24",    "https://dlm2.download.intuit.com/akdlm/SBD/QuickBooks/2024/LatestAcc/QuickBooksEnterprise24.exe"),
    ("QuickBooks Enterprise 23",         "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2023/Latest/QuickBooksEnterprise23.exe"),
    ("QuickBooks Enterprise 22",         "https://DLM2.download.intuit.com/akdlm/SBD/QuickBooks/2022/Latest/QuickBooksEnterprise22.exe"),
]

print(f"{'Product':<40} {'Last Modified':<32} {'Size (MB)'}")
print("-" * 85)

results = {}

for name, url in versions:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            last_mod = resp.headers.get("Last-Modified", "N/A")
            size = int(resp.headers.get("Content-Length", 0))
            size_mb = size // (1024 * 1024)
            # Parse and reformat date
            try:
                dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z")
                last_mod = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
            print(f"{name:<40} {last_mod:<32} {size_mb} MB")
            results[name] = {"last_modified": last_mod, "size_mb": size_mb}
    except Exception as e:
        print(f"{name:<40} ERROR: {e}")
        results[name] = {"error": str(e)}

with open("versions.json", "w") as f:
    json.dump(results, f, indent=2)
