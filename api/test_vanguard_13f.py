import os
import requests
import json
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import pandas as pd

# Vanguard Group CIK
CIK = "0000102909"
USER_AGENT = os.getenv("SEC_USER_AGENT", "AIAnalyst/1.0")

headers = {"User-Agent": USER_AGENT}

def get_filings():
    url = f"https://data.sec.gov/submissions/CIK{CIK}.json"
    print(f"Fetching filings from {url}...")
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("Failed to fetch filings")
        return None
    return resp.json()

def get_xml_url(accession, primary_doc):
    # https://www.sec.gov/Archives/edgar/data/102909/000010290924000012/xslForm13F_X02/primary_doc.xml
    # Actually the structure is:
    # https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION_NO_DASHES}/{PRIMARY_DOC}
    acc_no_dash = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{CIK.lstrip('0')}/{acc_no_dash}/{primary_doc}"

def parse_13f(xml_url):
    print(f"Fetching XML: {xml_url}")
    resp = requests.get(xml_url, headers=headers)
    if resp.status_code != 200:
        print("Failed to fetch XML")
        return []
    
    # Modern 13F is an "InfoTable" structure
    # Sometimes primary_doc is the main page, and the info table is separate.
    # Let's inspect content briefly
    if b"<xml" not in resp.content[:100] and b"<ns" not in resp.content[:100]:
         # It might be an HTML index page.
         pass

    # Try simple parsing
    try:
        # Check if it has namespace
        root = ET.fromstring(resp.content)
        # Namespaces are annoying in SEC XML, usually {http://www.sec.gov/edgar/document/thirteenf/informationtable}
        # We'll traverse blindly
        holdings = []
        for info in root.findall(".//{*}infoTable"):
            issuer = info.find(".//{*}nameOfIssuer").text
            cusip = info.find(".//{*}cusip").text
            value = float(info.find(".//{*}value").text)
            shares = float(info.find(".//{*}shrsOrPrnAmt/{*}sshPrnamt").text)
            
            holdings.append({
                "issuer": issuer,
                "cusip": cusip,
                "value": value,
                "shares": shares
            })
        return pd.DataFrame(holdings)
    except Exception as e:
        print(f"XML Parsing Error: {e}")
        return pd.DataFrame()

def main():
    data = get_filings()
    if not data: return
    
    recent = data['filings']['recent']
    
    # Find last 2 13F-HR
    forms_13f = []
    for i, form in enumerate(recent['form']):
        if form == '13F-HR':
            forms_13f.append({
                "acc": recent['accessionNumber'][i],
                "doc": recent['primaryDocument'][i],
                "date": recent['filingDate'][i]
            })
            if len(forms_13f) >= 2: break
            
    print(f"Found {len(forms_13f)} recent 13F-HR filings")
    
    # Sometimes primaryDocument is .html (the index), and the actual XML is different. 
    # For Vanguard, usually they submit XML directly as primary?
    # Let's check the first one.
    
    # Wait: The "Information Table" is what we want.
    # The primary doc is usually the Cover Page. The Info Table is a separate document in the submission.
    # We need to list the documents in the accession directory to find "xml" info table.
    
    # Correction: Parsing just primary_doc might fail if it's just the cover page.
    # We'll just fetch the directory listing page for the first one to debug.
    
    latest = forms_13f[0]
    acc_no_dash = latest['acc'].replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK.lstrip('0')}/{acc_no_dash}/index.json"
    
    print(f"Checking index: {index_url}")
    # Fallback to HTML index
    index_page_url = f"https://www.sec.gov/Archives/edgar/data/{CIK.lstrip('0')}/{acc_no_dash}/{latest['acc']}-index.html"
    print(f"Fetching Index HTML: {index_page_url}")
    
    idx_resp = requests.get(index_page_url, headers=headers)
    if idx_resp.status_code == 200:
        soup = BeautifulSoup(idx_resp.content, 'html.parser')
        # Look for a link to an XML file that looks like an info table
        # Structure: Tables with "Document Type" -> "INFORMATION TABLE" -> Document Name .xml
        
        xml_link = None
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) > 3:
                doc_type = cells[1].text.strip()
                doc_name = cells[2].text.strip()
                if "INFORMATION TABLE" in doc_type.upper() and doc_name.endswith(".xml"):
                    xml_href = cells[2].find("a")["href"]
                    # link is relative: /Archives/edgar/data/...
                    xml_link = f"https://www.sec.gov{xml_href}"
                    break
        
        if xml_link:
            print(f"Found InfoTable XML: {xml_link}")
            df = parse_13f(xml_link)
            if not df.empty:
                print(f"Extracted {len(df)} holdings.")
                print("Top 5 by Value:")
                print(df.sort_values("value", ascending=False).head(5)[['issuer', 'value', 'shares']])
        else:
            print("Could not find INFORMATION TABLE xml link in index page.")
    else:
        print(f"Failed to fetch index page: {idx_resp.status_code}")

if __name__ == "__main__":
    main()
