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


def get_msi_properties(msi_path):
    """Return (ProductName, ProductVersion) from an MSI file, or (None, None) on failure."""
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


def find_quickbooks_version(search_dir, _depth=0):
    """
    Find the actual QuickBooks ProductVersion from an extracted installer directory.

    QuickBooks .exe installers contain a small bootstrapper MSI (consistently
    versioned 2.2.0.0) plus the real application payload, which may be a
    differently-named MSI or packed inside .cab archives.  This function:
      1. Collects every .msi under search_dir, sorted largest-first.
      2. Prefers an MSI whose ProductName contains "QuickBooks" over any other.
      3. Falls back to the first MSI whose version differs from the known
         bootstrapper version (2.2.0.0).
      4. If still nothing useful, extracts each .cab file found and recurses
         (up to depth 2) to handle nested payloads.
    """
    if _depth > 2:
        return None

    msi_files = []
    cab_files = []
    for root, dirs, files in os.walk(search_dir):
        for f in files:
            full_path = os.path.join(root, f)
            lower_f = f.lower()
            if lower_f.endswith(".msi"):
                msi_files.append(full_path)
            elif lower_f.endswith(".cab"):
                cab_files.append(full_path)

    # Largest MSI first – the application MSI is typically much bigger than the
    # bootstrapper, so this ordering maximizes the chance of an early match.
    msi_files.sort(key=os.path.getsize, reverse=True)

    fallback_version = None

    for msi_path in msi_files:
        prod_name, prod_ver = get_msi_properties(msi_path)
        if not prod_ver:
            continue
        if prod_name and "quickbooks" in prod_name.lower():
            # Found the real application MSI – use it regardless of version value.
            print(f"    [msi] {os.path.basename(msi_path)}: {prod_name} {prod_ver}")
            return prod_ver
        if prod_ver != "2.2.0.0" and fallback_version is None:
            fallback_version = prod_ver

    if fallback_version:
        return fallback_version

    # No suitable MSI found in this pass – dig into any .cab archives.
    for cab_path in cab_files:
        nested_dir = tempfile.mkdtemp()
        try:
            r = subprocess.run(
                ["7z", "x", cab_path, "-aoa", f"-o{nested_dir}"],
                capture_output=True
            )
            if r.returncode == 0:
                ver = find_quickbooks_version(nested_dir, _depth + 1)
                if ver:
                    return ver
        finally:
            shutil.rmtree(nested_dir, ignore_errors=True)

    # Absolute last resort: return the version from the first MSI that has one
    # (likely the bootstrapper), so we at least report something rather than "unknown".
    for msi_path in msi_files:
        _, prod_ver = get_msi_properties(msi_path)
        if prod_ver:
            return prod_ver

    return None


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

        # Find the real QuickBooks version from the extracted content
        version = find_quickbooks_version(tmp_dir)

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
