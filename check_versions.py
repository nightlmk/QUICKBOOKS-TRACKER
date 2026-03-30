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


def read_msi_version(msi_path):
    """
    Return (ProductName, ProductVersion) from quickbooks.msi via msiinfo, or
    (None, None) on failure.
    """
    result = subprocess.run(
        ["msiinfo", "export", msi_path, "Property"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None, None
    prod_name = None
    prod_ver = None
    for line in result.stdout.splitlines():
        if line.startswith("ProductName\t"):
            prod_name = line.split("\t", 1)[1].strip()
        elif line.startswith("ProductVersion\t"):
            prod_ver = line.split("\t", 1)[1].strip()
    return prod_name, prod_ver


def find_quickbooks_msi(search_dir):
    """
    Recursively search search_dir for every file named quickbooks.msi (any case).

    Extracting a QB .exe produces at least two copies of quickbooks.msi:
      - A small top-level bootstrapper (version 2.2.0.0)
      - The real application MSI nested in a sub-folder (e.g. QBooks/quickbooks.msi)
        which carries the true product version and is always much larger.

    Returns the path of the largest quickbooks.msi found, which is the real
    application installer.  Returns None if no such file exists.
    """
    candidates = []
    for root, dirs, files in os.walk(search_dir):
        for f in files:
            if f.lower() == "quickbooks.msi":
                full_path = os.path.join(root, f)
                candidates.append(full_path)

    if not candidates:
        return None

    # The real application MSI is much larger than the bootstrapper, so pick
    # the largest one.
    candidates.sort(key=os.path.getsize, reverse=True)
    for path in candidates:
        print(f"    [found] {path} ({os.path.getsize(path):,} bytes)")
    return candidates[0]


for name, url in versions:
    print(f"Processing {name}...")
    tmp_fd, tmp_exe = tempfile.mkstemp(suffix=".exe")
    os.close(tmp_fd)
    tmp_dir = tempfile.mkdtemp()
    try:
        # 1. Download the installer
        urllib.request.urlretrieve(url, tmp_exe)

        # 2. Get Last-Modified and Content-Length from headers
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as r:
            last_mod = r.headers.get("Last-Modified", "")
            size_mb = round(int(r.headers.get("Content-Length", 0)) / (1024 * 1024))

        # 3. Extract the .exe with 7-Zip
        extract = subprocess.run(["7z", "x", tmp_exe, "-aoa", f"-o{tmp_dir}"], capture_output=True)
        if extract.returncode != 0:
            raise RuntimeError(f"7z extraction failed: {extract.stderr.decode(errors='replace')}")

        # 4. Find quickbooks.msi (pick the largest one – that is the real app installer)
        msi_path = find_quickbooks_msi(tmp_dir)
        if not msi_path:
            raise RuntimeError("quickbooks.msi not found in extracted installer")

        # 5. Read ProductName and ProductVersion from the MSI
        prod_name, version = read_msi_version(msi_path)
        if not version:
            raise RuntimeError(f"ProductVersion not found in {msi_path}")
        print(f"    ProductName: {prod_name}")

        # Parse date
        try:
            dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = last_mod

        results.append({
            "name": name,
            "version": version,
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
