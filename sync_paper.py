import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time
import argparse
import re

API_URL = "http://127.0.0.1:6806"
API_TOKEN = "bqrrmb48o36gbpo2"
NOTEBOOK_ID = "20260525213703-by7xgsc"

def call_api(endpoint, data):
    url = f"{API_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Token {API_TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as res:
            response_data = res.read().decode("utf-8")
            return json.loads(response_data)
    except Exception as e:
        print(f"Error calling {endpoint}: {e}")
        return None

def fetch_arxiv_metadata(arxiv_id):
    print(f"Fetching metadata from ArXiv API for ID: {arxiv_id}...")
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        with urllib.request.urlopen(url) as res:
            xml_data = res.read()
            return parse_arxiv_xml(xml_data, arxiv_id)
    except Exception as e:
        print(f"Error fetching from ArXiv: {e}")
        return None

def parse_arxiv_xml(xml_data, arxiv_id):
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    try:
        root = ET.fromstring(xml_data)
        entry = root.find('atom:entry', namespaces)
        if entry is None:
            print("No entry found in ArXiv XML.")
            return None
        
        # Get Title
        title_elem = entry.find('atom:title', namespaces)
        title = "Untitled"
        if title_elem is not None and title_elem.text:
            title = title_elem.text.strip().replace('\n', ' ')
            title = re.sub(r'\s+', ' ', title)
            
        # Get Summary (Abstract)
        summary_elem = entry.find('atom:summary', namespaces)
        summary = ""
        if summary_elem is not None and summary_elem.text:
            summary = summary_elem.text.strip().replace('\n', ' ')
            summary = re.sub(r'\s+', ' ', summary)
            
        # Get Authors
        authors = []
        for author in entry.findall('atom:author', namespaces):
            name_elem = author.find('atom:name', namespaces)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())
        authors_str = ", ".join(authors)
        
        # Get Published Date
        published_elem = entry.find('atom:published', namespaces)
        published = ""
        if published_elem is not None and published_elem.text:
            published = published_elem.text.strip()
            if len(published) >= 10:
                published = published[:10]
                
        # Get PDF Link
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        for link in entry.findall('atom:link', namespaces):
            title_attr = link.attrib.get('title')
            type_attr = link.attrib.get('type')
            if title_attr == 'pdf' or type_attr == 'application/pdf':
                pdf_url = link.attrib.get('href', pdf_url)
                break
                
        return {
            "title": title,
            "summary": summary,
            "authors": authors_str,
            "published": published,
            "pdf_url": pdf_url,
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}"
        }
    except Exception as e:
        print(f"Error parsing ArXiv XML: {e}")
        return None

def resolve_path(hpath):
    parts = [p for p in hpath.split('/') if p]
    current_id_path = "/"
    
    for part in parts:
        res = call_api("/api/filetree/listDocsByPath", {
            "notebook": NOTEBOOK_ID,
            "path": current_id_path
        })
        if not res or res.get("code") != 0:
            return None
        
        files = res.get("data", {}).get("files", [])
        found_id = None
        for f in files:
            if f.get("name") == part:
                found_id = f.get("id")
                break
        
        if not found_id:
            return None
            
        if current_id_path == "/":
            current_id_path = f"/{found_id}"
        else:
            current_id_path = f"{current_id_path}/{found_id}"
            
    return current_id_path

def extract_section(md, section_title):
    marker = f"## [{section_title}]"
    idx = md.find(marker)
    if idx == -1:
        marker = f"## {section_title}"
        idx = md.find(marker)
        if idx == -1:
            return None
            
    start_pos = idx + len(marker)
    
    # Find next header "## " or horizontal rule "---"
    end_pos = len(md)
    next_header = md.find("\n## ", start_pos)
    next_hr = md.find("\n---", start_pos)
    
    if next_header != -1 and next_hr != -1:
        end_pos = min(next_header, next_hr)
    elif next_header != -1:
        end_pos = next_header
    elif next_hr != -1:
        end_pos = next_hr
        
    content = md[start_pos:end_pos].strip()
    return content

def sanitize_title(title):
    sanitized = re.sub(r'[\/:*?"<>|]', ' -', title)
    return sanitized.strip()

def find_existing_document(venue, title):
    folder_path = f"/01_Papers/{venue}"
    resolved_id_path = resolve_path(folder_path)
    if not resolved_id_path:
        return None
        
    res = call_api("/api/filetree/listDocsByPath", {
        "notebook": NOTEBOOK_ID,
        "path": resolved_id_path
    })
    if res and res.get("code") == 0:
        files = res.get("data", {}).get("files", [])
        for f in files:
            if f.get("name").lower() == title.lower():
                return f.get("id")
    return None

def generate_markdown(meta, reading_notes=None, judgment=None, draft_review=None,
                      ai_draft=None, knowledge_ext=None, backfeed_status=None,
                      share_decision=None, next_action=None):
    
    # Preserve existing content or write default templates
    notes_content = reading_notes if reading_notes else """> [!IMPORTANT]
> *人工阅读记录。任何自动同步工具均绝对禁止覆盖或清空此分区。*
*   **阅读时间**: 
*   **精读笔记**: 
    *   (在此记录您的阅读细节、推导过程、关键公式或模型架构的独特理解)"""

    judgment_content = judgment if judgment else """> [!IMPORTANT]
> *人工思考与批判性判断。任何自动同步工具均绝对禁止覆盖或清空此分区。*
*   **论文盲点/局限性**: 
*   **实验设计局限**: 
*   **我的评价**: 
    *   (在这里写下您对该文的真实技术评价，是否真正解决了痛点？)"""

    review_content = draft_review if draft_review else """> [!IMPORTANT]
> *人工对 AI 生成草稿的审查记录，自动更新不会覆盖。*
*   **AI Draft 是否可信**: High / Medium / Low
*   **错误点**: 
*   **我修正后的理解**: 
*   **是否需要重新生成**: """

    ai_draft_content = ai_draft if ai_draft else f"""> [!NOTE]
> *This section is auto-generated by AI.*
*   **一句话总结**: 作者认为 ______，因此提出 ______。
*   **解决的问题**: {meta.get('summary', '')[:300]}...
*   **核心方法**: 
*   **实验结论**: """

    knowledge_ext_content = knowledge_ext if knowledge_ext else """*   **可提炼的方法/技术路线**: ➔ [[方法或机制链接]]
*   **可引入的问题意识/技术冲突**: ➔ [[问题意识链接]]
*   **有启发的后续实验设计**: """

    backfeed_status_content = backfeed_status if backfeed_status else """*   [ ] 已回流 Topic 页面
*   [ ] 已回流 Method 页面
*   [ ] 已回流 Problem 页面
*   [ ] 已加入 Share 候选池
*   [ ] 已更新 阅读后思考索引"""

    share_decision_content = share_decision if share_decision else """*   **是否值得分享**: 是/否
*   **分享主题建议**: 
*   **分享目标受众**: """

    next_action_content = next_action if next_action else """*   [ ] (例如：复现代码 / 寻找对比实验基线 / 推荐给组内同学)"""

    md = f"""# {meta['title']}

## [Auto Metadata]
*   **Venue**: {meta.get('venue', 'Unknown')}
*   **Authors**: {meta.get('authors', 'Unknown')}
*   **Published**: {meta.get('published', 'Unknown')}
*   **Source**: {meta.get('source', 'Unknown')}
*   **Status**: {meta.get('status', 'Unknown')}
*   **Data Origin**: {meta.get('data_origin', 'Unknown')}
*   **Type**: #LLM / #VLM / #VideoLMM / #Agent
*   **Tags**: #Unread
*   **Priority**: High / Medium / Low
*   **URL**: [Abstract URL]({meta.get('abs_url', '')})
*   **PDF**: [PDF URL]({meta.get('pdf_url', '')})

## [AI Draft Summary]
{ai_draft_content}

## [AI Draft Review]
{review_content}

## [My Reading Notes]
{notes_content}

## [My Judgment]
{judgment_content}

## [Knowledge Extraction]
{knowledge_ext_content}

## [Knowledge Backfeed Status]
{backfeed_status_content}

## [Share Decision]
{share_decision_content}

## [Next Action]
{next_action_content}

---
*回到主入口: [[总入口]]*"""
    return md

def main():
    parser = argparse.ArgumentParser(description="Sync ArXiv Paper to SiYuan Notes (CLI Prototype)")
    parser.add_argument("--url", required=True, help="ArXiv URL (abs or pdf)")
    parser.add_argument("--venue", required=True, help="Suggested folder in 01_Papers (e.g., ICLR_2025, NeurIPS_2025)")
    parser.add_argument("--source", default="arxiv", help="Source system (arxiv / openreview / acl / cvf)")
    parser.add_argument("--status", default="preprint", help="Status (preprint / accepted / unknown)")
    parser.add_argument("--data_origin", default="arxiv_api", help="Data origin (arxiv_api / manual_import)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite metadata and AI summaries only, protecting human notes")
    args = parser.parse_args()
    
    # Extract ArXiv ID
    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)', args.url)
    if not match:
        print("Error: Could not parse ArXiv ID from URL.")
        return
    arxiv_id = match.group(1)
    
    # Fetch metadata
    meta = fetch_arxiv_metadata(arxiv_id)
    if not meta:
        print("Error: Failed to fetch metadata.")
        return
        
    # Enforce routing rules
    source = args.source
    status = args.status
    data_origin = args.data_origin
    
    target_venue = args.venue
    if source == "arxiv" and status in ["preprint", "unknown"]:
        print("Paper is a preprint. Routing to 'ArXiv_Preprints' folder.")
        target_venue = "ArXiv_Preprints"
    elif status == "accepted":
        print(f"Paper is accepted. Routing to meeting folder: '{args.venue}'.")
        target_venue = args.venue
    else:
        if args.venue not in ["ArXiv_Preprints", "Manual_Import"]:
            print(f"Paper is not confirmed accepted (status='{status}'). Routing to 'Manual_Import' to avoid conference folder clutter.")
            target_venue = "Manual_Import"
            
    meta["venue"] = target_venue
    meta["source"] = source
    meta["status"] = status
    meta["data_origin"] = data_origin
    
    sanitized_title = sanitize_title(meta["title"])
    doc_id = find_existing_document(target_venue, sanitized_title)
    
    if doc_id:
        print(f"Document already exists (ID: {doc_id}). Evaluating sync strategy...")
        print("Fetching existing Markdown content...")
        doc_res = call_api("/api/export/exportMdContent", {"id": doc_id})
        if doc_res and doc_res.get("code") == 0:
            existing_md = doc_res.get("data", {}).get("content", "")
            
            # ALWAYS extract and protect human zones
            reading_notes = extract_section(existing_md, "My Reading Notes")
            judgment = extract_section(existing_md, "My Judgment")
            draft_review = extract_section(existing_md, "AI Draft Review")
            
            if args.overwrite:
                print("  --overwrite provided. Updating [Auto Metadata] and [AI Draft Summary] only. Protecting manual notes.")
                md = generate_markdown(meta, reading_notes, judgment, draft_review)
                res = call_api("/api/block/updateBlock", {
                    "id": doc_id,
                    "dataType": "markdown",
                    "data": md
                })
                print("Update response:", res.get("code"))
            else:
                print("  Default sync (no --overwrite). Preserving ALL fields except [Auto Metadata].")
                # Extract and preserve all manually/AI filled fields
                ai_draft = extract_section(existing_md, "AI Draft Summary")
                knowledge_ext = extract_section(existing_md, "Knowledge Extraction")
                backfeed_status = extract_section(existing_md, "Knowledge Backfeed Status")
                share_decision = extract_section(existing_md, "Share Decision")
                next_action = extract_section(existing_md, "Next Action")
                
                md = generate_markdown(meta, reading_notes, judgment, draft_review,
                                       ai_draft, knowledge_ext, backfeed_status,
                                       share_decision, next_action)
                res = call_api("/api/block/updateBlock", {
                    "id": doc_id,
                    "dataType": "markdown",
                    "data": md
                })
                print("Update response:", res.get("code"))
        else:
            print("  Error exporting existing content. Aborting to protect data.")
    else:
        print(f"Creating new paper card under '/01_Papers/{target_venue}'...")
        md = generate_markdown(meta)
        path = f"/01_Papers/{target_venue}/{sanitized_title}"
        res = call_api("/api/filetree/createDocWithMd", {
            "notebook": NOTEBOOK_ID,
            "path": path,
            "markdown": md
        })
        print("Create response:", res.get("code"))

if __name__ == "__main__":
    main()
