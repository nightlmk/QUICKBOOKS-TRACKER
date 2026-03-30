import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone

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

results = []

for name, url in versions:
    print(f"Processing {name}...")
    tmp_fd, tmp_exe = tempfile.mkstemp(suffix=".exe")
    os.close(tmp_fd)
    tmp_dir = tempfile.mkdtemp()
    try:
        # Download
        urllib.request.urlretrieve(url, tmp_exe)

        # Get Last-Modified and Content-Length from headers
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as r:
            last_mod = r.headers.get("Last-Modified", "")
            size_mb = round(int(r.headers.get("Content-Length", 0)) / (1024 * 1024))

        # Extract exe
        extract = subprocess.run(["7z", "x", tmp_exe, "-aoa", f"-o{tmp_dir}"], capture_output=True)
        if extract.returncode != 0:
            raise RuntimeError(f"7z extraction failed: {extract.stderr.decode(errors='replace')}")

        # Find quickbooks.msi
        msi_path = None
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                if f.lower() == "quickbooks.msi":
                    msi_path = os.path.join(root, f)
                    break

        version = None
        if msi_path:
            msi_result = subprocess.run(
                ["msiinfo", "export", msi_path, "Property"],
                capture_output=True, text=True
            )
            if msi_result.returncode == 0:
                for line in msi_result.stdout.splitlines():
                    if line.startswith("ProductVersion"):
                        version = line.split("\t")[1].strip()
                        break

        # Parse date
        try:
            dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = last_mod

        results.append({
            "name": name,
            "version": version or "unknown",
            "last_modified": date_str,
            "size_mb": size_mb,
        })
        print(f"  -> {version} ({date_str})")

    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"name": name, "version": "unknown", "last_modified": "", "size_mb": 0, "error": str(e)})
    finally:
        if os.path.exists(tmp_exe):
            os.remove(tmp_exe)
        shutil.rmtree(tmp_dir, ignore_errors=True)

output = {
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "versions": results,
}

with open("versions.json", "w") as f:
    json.dump(output, f, indent=2)

print("Done. versions.json updated.")
