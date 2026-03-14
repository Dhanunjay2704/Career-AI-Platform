import os
import re
import requests
import gradio as gr
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import Tool
from langchain.tools import tool
from langchain.agents import create_agent

# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
RAPID_API_KEY  = os.getenv("RAPID_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ==========================================
# Shared LLM initializer
# ==========================================

def get_model():
    return init_chat_model(
        model="gemini-2.5-flash",
        model_provider="google_genai",
        api_key=GEMINI_API_KEY
    )

# ==========================================
# Shared RapidAPI job fetcher
# ==========================================

def fetch_jobs_rapidapi(query_str: str) -> list:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": query_str,
        "page": "1",
        "country": "in",
        "employment_types": "INTERN,FULLTIME",
        "job_requirements": "no_experience,under_3_years_experience"
    }
    try:
        resp = requests.get(url, headers=headers, params=params)
        return resp.json().get("data", [])
    except Exception:
        return []

# ==========================================
# Shared HTML helpers
# ==========================================

def badge(text, bg, color):
    return (f'<span style="background:{bg} !important;color:{color} !important;'
            f'font-size:0.75rem;font-weight:600;padding:3px 10px;border-radius:20px;'
            f'display:inline-block;margin:2px">{text}</span>')

def sec_title(text):
    return (f'<div style="font-size:1.05rem !important;font-weight:700 !important;'
            f'color:#111111 !important;margin:0 0 14px !important;'
            f'display:flex;align-items:center;gap:8px">{text}</div>')

def card_wrap(content, border="#e5e7eb", bg="#ffffff"):
    return (f'<div style="background:{bg} !important;border:1px solid {border};'
            f'border-radius:12px;padding:16px 20px;margin-bottom:12px;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.06)">{content}</div>')

def title_div(text, color="#111111"):
    return (f'<div style="font-size:0.95rem !important;font-weight:700 !important;'
            f'color:{color} !important;margin-bottom:8px">{text}</div>')

def body_div(text, color="#4b5563"):
    return (f'<div style="font-size:0.85rem !important;color:{color} !important;'
            f'line-height:1.5;margin-bottom:8px">{text}</div>')

def apply_link(href, label="Apply Now"):
    if not href:
        return ""
    return (f'<a href="{href}" target="_blank" style="font-size:0.8rem !important;'
            f'font-weight:600 !important;color:#4f46e5 !important;'
            f'text-decoration:none !important">🔗 {label}</a>')

def regex_ex(field, text):
    m = re.search(rf"{field}:\s*(.+)", text)
    return m.group(1).strip() if m else ""

def wrap_html(inner):
    return f'<div style="font-family:Segoe UI,sans-serif;max-width:860px;margin:0 auto">{inner}</div>'

def error_html(msg):
    return f'<div style="color:#b91c1c;padding:16px;background:#fef2f2;border-radius:8px">❌ {msg}</div>'

def fallback_html(raw):
    safe = raw.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return f'<div style="font-size:0.9rem;line-height:1.8;color:#374151">{safe}</div>'

# ==========================================
# AGENT 1 — Skill to Career Mapper
# ==========================================

_agent1 = None

def get_agent1():
    global _agent1
    if _agent1:
        return _agent1

    model = get_model()

    skill_demand_tool = TavilySearch(
        max_results=5, topic="general", search_depth="advanced",
        tavily_api_key=TAVILY_API_KEY
    )

    @tool
    def search_jobs_a1(skill: str, location: str) -> list:
        """Search for jobs requiring a specific skill using JSearch API."""
        jobs = fetch_jobs_rapidapi(f"{skill} in {location}")
        return [{"company_name": j.get("employer_name",""), "job_title": j.get("job_title",""),
                 "location": j.get("job_city",""), "job_description": j.get("job_description",""),
                 "apply_link": j.get("job_apply_link","")} for j in jobs]

    _agent1 = create_agent(
        model=model,
        tools=[skill_demand_tool, search_jobs_a1],
        system_prompt=(
            "You are a Skill-to-Career Mapping assistant.\n"
            "Structure your response EXACTLY like this:\n\n"
            "DEMAND_SECTION:\n"
            "- [insight 1]\n- [insight 2]\n- [insight 3]\n- [insight 4]\n- [insight 5]\n\n"
            "JOBS_SECTION:\n"
            "JOB_START\nTITLE: [title]\nCOMPANY: [company]\nLOCATION: [location]\n"
            "DESCRIPTION: [2-3 sentences]\nLINK: [apply link]\nJOB_END\n\n"
            "No markdown. Follow format strictly."
        )
    )
    return _agent1

def format_agent1(raw):
    html = ""
    d = re.search(r"DEMAND_SECTION:(.*?)(?:JOBS_SECTION:|$)", raw, re.DOTALL)
    if d:
        lines = [l.strip().lstrip("-•*").strip() for l in d.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        inner = "".join(f'<div style="padding:7px 0;border-bottom:1px solid #dde3f8;font-size:0.92rem !important;color:#1a1a2e !important;display:flex;gap:8px"><span style="color:#6366f1;flex-shrink:0">✦</span><span style="color:#1a1a2e !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#eef1ff !important;border-left:4px solid #6366f1;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("📊 Industry Demand & Insights")}{inner}</div>'

    j = re.search(r"JOBS_SECTION:(.*?)$", raw, re.DOTALL)
    if j:
        blocks = re.findall(r"JOB_START(.*?)JOB_END", j.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"💼 Job Openings ({len(blocks)} found)")
            for b in blocks:
                t = regex_ex("TITLE", b); c = regex_ex("COMPANY", b)
                lo = regex_ex("LOCATION", b) or "Not specified"
                de = regex_ex("DESCRIPTION", b); li = regex_ex("LINK", b)
                html += card_wrap(
                    title_div(t) +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(f"🏢 {c}", "#ede9fe", "#4c1d95")}{badge(f"📍 {lo}", "#ecfdf5", "#065f46")}</div>' +
                    body_div(de) + apply_link(li)
                )
    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent1(skill, location, custom_query):
    if not skill.strip() and not custom_query.strip():
        return error_html("Please enter a skill or custom query.")
    query = custom_query.strip() if custom_query.strip() else f"Demand for {skill} and job openings in {location or 'India'}"
    try:
        r = get_agent1().invoke({"messages": [{"role": "user", "content": query}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent1(raw)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# AGENT 2 — Interview Prep Agent
# ==========================================

_agent2 = None

def get_agent2():
    global _agent2
    if _agent2:
        return _agent2

    model = get_model()

    iq = TavilySearch(name="interview_questions_search",
        description="Search for common interview questions for a given role and level.",
        max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)
    pt = TavilySearch(name="prep_tips_search",
        description="Search for preparation tips and strategies for interview prep.",
        max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)
    rf = TavilySearch(name="resource_finder_search",
        description="Find YouTube videos, blogs, and courses for interview preparation.",
        max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)

    _agent2 = create_agent(
        model=model, tools=[iq, pt, rf],
        system_prompt=(
            "You are an Interview Prep assistant.\n"
            "Structure your response EXACTLY like this:\n\n"
            "QUESTIONS_SECTION:\n"
            + "".join(f"- [question {i}]\n" for i in range(1,21)) +
            "\nTIPS_SECTION:\n"
            + "".join(f"- [tip {i}]\n" for i in range(1,8)) +
            "\nRESOURCES_SECTION:\n"
            "RESOURCE_START\nTITLE: [title]\nTYPE: [YouTube/Blog/Course]\n"
            "LINK: [url]\nDESCRIPTION: [one sentence]\nRESOURCE_END\n\n"
            "Always generate exactly 20 questions, 7 tips, at least 3 resources.\n"
            "No markdown. Follow format strictly."
        )
    )
    return _agent2

def format_agent2(raw):
    html = ""
    q = re.search(r"QUESTIONS_SECTION:(.*?)(?:TIPS_SECTION:|$)", raw, re.DOTALL)
    if q:
        lines = [l.strip().lstrip("-•*").strip() for l in q.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:9px 0;border-bottom:1px solid #c7d0f8;font-size:0.92rem !important;color:#1a1a2e !important;display:flex;gap:10px;align-items:flex-start"><span style="background:#6366f1 !important;color:#fff !important;font-size:0.72rem;font-weight:700;border-radius:50%;min-width:22px;height:22px;display:flex;align-items:center;justify-content:center;flex-shrink:0">{i}</span><span style="color:#1a1a2e !important">{l}</span></div>' for i,l in enumerate(lines,1))
        html += f'<div style="background:#eef1ff !important;border-left:4px solid #6366f1;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("❓ Interview Questions")}{items}</div>'

    t = re.search(r"TIPS_SECTION:(.*?)(?:RESOURCES_SECTION:|$)", raw, re.DOTALL)
    if t:
        lines = [l.strip().lstrip("-•*").strip() for l in t.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #bbf7d0;font-size:0.9rem !important;color:#14532d !important;display:flex;gap:8px"><span style="color:#22c55e;flex-shrink:0">✦</span><span style="color:#14532d !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#ecfdf5 !important;border-left:4px solid #22c55e;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("💡 Preparation Tips")}{items}</div>'

    r = re.search(r"RESOURCES_SECTION:(.*?)$", raw, re.DOTALL)
    if r:
        blocks = re.findall(r"RESOURCE_START(.*?)RESOURCE_END", r.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"📚 Resources ({len(blocks)} found)")
            for b in blocks:
                ti = regex_ex("TITLE", b); rt = regex_ex("TYPE", b).lower()
                li = regex_ex("LINK", b); de = regex_ex("DESCRIPTION", b)
                bc = ("badge-yt" if "youtube" in rt else "badge-blog" if "blog" in rt else "badge-course")
                bg_map = {"badge-yt":"#fee2e2","badge-blog":"#fef9c3","badge-course":"#ede9fe"}
                cl_map = {"badge-yt":"#b91c1c","badge-blog":"#713f12","badge-course":"#5b21b6"}
                html += card_wrap(
                    f'<div style="display:flex;gap:14px;align-items:flex-start">'
                    f'{badge(rt.capitalize() or "Resource", bg_map.get(bc,"#f1f5f9"), cl_map.get(bc,"#334155"))}'
                    f'<div><div style="font-size:0.92rem !important;font-weight:700 !important;color:#111111 !important;margin-bottom:4px">{ti}</div>'
                    f'<div style="font-size:0.83rem !important;color:#4b5563 !important;margin-bottom:8px">{de}</div>'
                    f'{apply_link(li, "Visit Resource →")}</div></div>'
                )
    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent2(role, level, round_type):
    if not role.strip():
        return error_html("Please enter a role name.")
    try:
        r = get_agent2().invoke({"messages": [{"role": "user", "content": f"Interview prep for {role} — Level: {level}, Round: {round_type}"}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent2(raw)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# AGENT 3 — Salary Insights Agent
# ==========================================

_agent3 = None

def get_agent3():
    global _agent3
    if _agent3:
        return _agent3

    model = get_model()
    serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)

    _agent3 = create_agent(
        model=model,
        tools=[
            Tool(name="salary_search", func=serper.run, description="Search salary ranges by experience level."),
            Tool(name="company_search", func=serper.run, description="Search top paying companies for a job title."),
            Tool(name="location_search", func=serper.run, description="Search city-wise salary comparison."),
        ],
        system_prompt=(
            "You are a Salary Insights assistant.\n"
            "Structure your response EXACTLY like this:\n\n"
            "SALARY_SECTION:\n- Fresher (0-2 yrs): [range]\n- Mid-level (2-5 yrs): [range]\n"
            "- Senior (5+ yrs): [range]\n- Average salary: [value]\n- Salary trend: [Rising/Stable/Declining]\n\n"
            "COMPANIES_SECTION:\nCOMPANY_START\nNAME: [name]\nPAY_RANGE: [range]\nLOCATION: [city]\nPERKS: [perks]\nCOMPANY_END\n\n"
            "LOCATION_SECTION:\n- [City]: [range] - [remark]\n\n"
            "SKILLS_SECTION:\n- [skill]: [boost %]\n\n"
            "Return at least 5 companies, 4 locations, 5 skills. No markdown. Follow strictly."
        )
    )
    return _agent3

def format_agent3(raw):
    html = ""
    s = re.search(r"SALARY_SECTION:(.*?)(?:COMPANIES_SECTION:|$)", raw, re.DOTALL)
    if s:
        lines = [l.strip().lstrip("-•*").strip() for l in s.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #c7d0f8;font-size:0.92rem !important;color:#1a1a2e !important;display:flex;gap:8px"><span style="color:#6366f1;flex-shrink:0">✦</span><span style="color:#1a1a2e !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#eef1ff !important;border-left:4px solid #6366f1;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("💰 Salary Insights")}{items}</div>'

    c = re.search(r"COMPANIES_SECTION:(.*?)(?:LOCATION_SECTION:|$)", raw, re.DOTALL)
    if c:
        blocks = re.findall(r"COMPANY_START(.*?)COMPANY_END", c.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"🏢 Top Paying Companies ({len(blocks)} found)")
            for b in blocks:
                n=regex_ex("NAME",b); p=regex_ex("PAY_RANGE",b); lo=regex_ex("LOCATION",b); pk=regex_ex("PERKS",b)
                html += card_wrap(
                    title_div(f"🏛 {n}") +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(f"💵 {p}","#dcfce7","#14532d")}{badge(f"📍 {lo}","#e0e7ff","#1e1b4b")}</div>' +
                    body_div(f"✨ {pk}")
                )

    l = re.search(r"LOCATION_SECTION:(.*?)(?:SKILLS_SECTION:|$)", raw, re.DOTALL)
    if l:
        lines = [li.strip().lstrip("-•*").strip() for li in l.group(1).splitlines() if li.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #fed7aa;font-size:0.92rem !important;color:#431407 !important;display:flex;gap:8px"><span style="color:#f97316;flex-shrink:0">◆</span><span style="color:#431407 !important">{li}</span></div>' for li in lines)
        html += f'<div style="background:#fff7ed !important;border-left:4px solid #f97316;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("📍 City-wise Salary Comparison")}{items}</div>'

    sk = re.search(r"SKILLS_SECTION:(.*?)$", raw, re.DOTALL)
    if sk:
        lines = [l.strip().lstrip("-•*").strip() for l in sk.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #bbf7d0;font-size:0.9rem !important;color:#14532d !important;display:flex;gap:8px"><span style="color:#22c55e;flex-shrink:0">✦</span><span style="color:#14532d !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#f0fdf4 !important;border-left:4px solid #22c55e;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("🚀 Skills That Boost Salary")}{items}</div>'

    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent3(job_title, location):
    if not job_title.strip():
        return error_html("Please enter a job title.")
    try:
        r = get_agent3().invoke({"messages": [{"role": "user", "content": f"Salary insights for {job_title} in {location or 'India'}"}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent3(raw)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# AGENT 4 — Course Finder Agent
# ==========================================

_agent4 = None

def get_agent4():
    global _agent4
    if _agent4:
        return _agent4

    model = get_model()
    serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)

    _agent4 = create_agent(
        model=model,
        tools=[
            Tool(name="free_courses_search", func=serper.run, description="Search free courses on Coursera, YouTube, Google, edX."),
            Tool(name="certification_search", func=serper.run, description="Search paid certifications from Google, Microsoft, AWS."),
            Tool(name="roadmap_search", func=serper.run, description="Search step-by-step learning roadmap for a skill."),
            Tool(name="platform_search", func=serper.run, description="Compare best platforms to learn a skill."),
        ],
        system_prompt=(
            "You are a Course Finder assistant.\n"
            "Structure your response EXACTLY like this:\n\n"
            "COURSES_SECTION:\nCOURSE_START\nTITLE: [title]\nPLATFORM: [platform]\n"
            "LEVEL: [level]\nDURATION: [duration]\nPRICE: Free\nCOURSE_END\n\n"
            "CERTIFICATIONS_SECTION:\nCERT_START\nNAME: [name]\nPROVIDER: [provider]\n"
            "COST: [cost]\nVALIDITY: [validity]\nCERT_END\n\n"
            "ROADMAP_SECTION:\nSTEP_START\nSTEP: [num]\nTITLE: [title]\n"
            "DESCRIPTION: [1-2 sentences]\nDURATION: [time]\nSTEP_END\n\n"
            "PLATFORMS_SECTION:\n- [Platform]: [what it offers]\n\n"
            "Return at least 5 courses, 4 certs, 6 roadmap steps, 5 platforms.\n"
            "Do NOT include URLs. No markdown. Follow strictly."
        )
    )
    return _agent4

def make_search_url(title, platform):
    return "https://www.google.com/search?q=" + f"{title} {platform}".replace(" ", "+")

def format_agent4(raw):
    html = ""
    c = re.search(r"COURSES_SECTION:(.*?)(?:CERTIFICATIONS_SECTION:|$)", raw, re.DOTALL)
    if c:
        blocks = re.findall(r"COURSE_START(.*?)COURSE_END", c.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"📚 Free Courses ({len(blocks)} found)")
            for b in blocks:
                ti=regex_ex("TITLE",b); pl=regex_ex("PLATFORM",b); lv=regex_ex("LEVEL",b)
                du=regex_ex("DURATION",b); pr=regex_ex("PRICE",b)
                pbg="#dcfce7" if "free" in pr.lower() else "#fef9c3"
                pcl="#14532d" if "free" in pr.lower() else "#713f12"
                html += card_wrap(
                    title_div(ti) +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(f"🌐 {pl}","#e0e7ff","#1e1b4b")}'
                    f'{badge(f"🆓 {pr}",pbg,pcl)}'
                    f'{badge(f"📊 {lv}","#f0f4ff","#1e1b4b")}'
                    f'{badge(f"⏱ {du}","#fff7ed","#431407")}</div>'
                    f'<a href="{make_search_url(ti,pl)}" target="_blank" style="font-size:0.8rem !important;font-weight:600 !important;color:#4f46e5 !important;text-decoration:none !important">🔍 Find this course</a>'
                )

    ce = re.search(r"CERTIFICATIONS_SECTION:(.*?)(?:ROADMAP_SECTION:|$)", raw, re.DOTALL)
    if ce:
        blocks = re.findall(r"CERT_START(.*?)CERT_END", ce.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"🏆 Certifications ({len(blocks)} found)")
            for b in blocks:
                n=regex_ex("NAME",b); p=regex_ex("PROVIDER",b); co=regex_ex("COST",b); v=regex_ex("VALIDITY",b)
                html += card_wrap(
                    title_div(f"🎓 {n}") +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(f"🏛 {p}","#fef3c7","#92400e")}'
                    f'{badge(f"💵 {co}","#fee2e2","#b91c1c")}'
                    f'{badge(f"✅ {v}","#d1fae5","#065f46")}</div>'
                    f'<a href="{make_search_url(n,p)}" target="_blank" style="font-size:0.8rem !important;font-weight:600 !important;color:#4f46e5 !important;text-decoration:none !important">🔍 Find this certification</a>',
                    bg="#fffbeb", border="#fde68a"
                )

    ro = re.search(r"ROADMAP_SECTION:(.*?)(?:PLATFORMS_SECTION:|$)", raw, re.DOTALL)
    if ro:
        steps = re.findall(r"STEP_START(.*?)STEP_END", ro.group(1), re.DOTALL)
        if steps:
            html += sec_title(f"🗺️ Learning Roadmap ({len(steps)} steps)")
            for s in steps:
                nu=regex_ex("STEP",s); ti=regex_ex("TITLE",s); de=regex_ex("DESCRIPTION",s); du=regex_ex("DURATION",s)
                html += (
                    f'<div style="background:#ffffff !important;border:1px solid #e5e7eb;border-radius:12px;'
                    f'padding:14px 18px;margin-bottom:10px;display:flex;gap:16px;align-items:flex-start">'
                    f'<div style="background:#6366f1 !important;color:#fff !important;font-size:0.85rem;font-weight:800;'
                    f'border-radius:50%;min-width:32px;height:32px;display:flex;align-items:center;justify-content:center;flex-shrink:0">{nu}</div>'
                    f'<div><div style="font-size:0.92rem !important;font-weight:700 !important;color:#111111 !important;margin-bottom:4px">{ti}</div>'
                    f'<div style="font-size:0.85rem !important;color:#4b5563 !important;line-height:1.5;margin-bottom:4px">{de}</div>'
                    f'<div style="font-size:0.78rem !important;color:#6366f1 !important;font-weight:600 !important">⏱ {du}</div></div></div>'
                )

    pl = re.search(r"PLATFORMS_SECTION:(.*?)$", raw, re.DOTALL)
    if pl:
        lines = [l.strip().lstrip("-•*").strip() for l in pl.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #dde3f8;font-size:0.9rem !important;color:#1a1a2e !important;display:flex;gap:8px"><span style="color:#6366f1;flex-shrink:0">◆</span><span style="color:#1a1a2e !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#f8faff !important;border-left:4px solid #6366f1;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("🌐 Best Platforms to Learn")}{items}</div>'

    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent4(skill, level):
    if not skill.strip():
        return error_html("Please enter a skill name.")
    try:
        r = get_agent4().invoke({"messages": [{"role": "user", "content": f"Find courses, certifications, roadmap and platforms for {skill} — Level: {level}"}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent4(raw)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# AGENT 5 — Startup Jobs Agent
# ==========================================

_agent5 = None

def get_agent5():
    global _agent5
    if _agent5:
        return _agent5

    model = get_model()

    s1 = TavilySearch(name="startup_search", description="Search top funded startups hiring in a domain.",
        max_results=6, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)
    s2 = TavilySearch(name="domain_trends_search", description="Search hiring trends and in-demand roles for a domain.",
        max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)
    s3 = TavilySearch(name="company_details_search", description="Search startup culture and perks for a domain.",
        max_results=5, search_depth="advanced", tavily_api_key=TAVILY_API_KEY)

    @tool
    def search_jobs_a5(skill: str, location: str) -> list:
        """Search real live startup job listings via RapidAPI."""
        jobs = fetch_jobs_rapidapi(f"{skill} startup jobs in {location}")
        return [{"job_title": j.get("job_title",""), "company_name": j.get("employer_name",""),
                 "location": j.get("job_city","Not specified"), "job_type": j.get("job_employment_type","Full-time"),
                 "description": j.get("job_description","")[:300], "apply_link": j.get("job_apply_link","")} for j in jobs]

    _agent5 = create_agent(
        model=model, tools=[s1, s2, s3, search_jobs_a5],
        system_prompt=(
            "You are a Startup Jobs assistant.\n"
            "Structure your response EXACTLY like this:\n\n"
            "STARTUPS_SECTION:\nSTARTUP_START\nNAME: [name]\nSTAGE: [Seed/Series A/Series B/Unicorn]\n"
            "SIZE: [size]\nDOMAIN: [domain]\nWHY_JOIN: [1-2 sentences]\nSTARTUP_END\n\n"
            "JOBS_SECTION:\nJOB_START\nTITLE: [title]\nCOMPANY: [company]\nLOCATION: [location]\n"
            "TYPE: [Full-time/Intern]\nDESCRIPTION: [2-3 sentences]\nLINK: [link]\nJOB_END\n\n"
            "TRENDS_SECTION:\n- [Role]: [why in demand]\n\n"
            "DOMAIN_SECTION:\n- [insight]\n\n"
            "Return at least 5 startups, all jobs from tool, 5 trends, 5 insights.\n"
            "For JOBS_SECTION use only data from search_jobs tool. No markdown. Follow strictly."
        )
    )
    return _agent5

def format_agent5(raw):
    html = ""
    s = re.search(r"STARTUPS_SECTION:(.*?)(?:JOBS_SECTION:|$)", raw, re.DOTALL)
    if s:
        blocks = re.findall(r"STARTUP_START(.*?)STARTUP_END", s.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"🏢 Top Startups ({len(blocks)} found)")
            stage_colors = {"seed":("#fef9c3","#713f12"),"series a":("#dbeafe","#1e3a8a"),"series b":("#ede9fe","#4c1d95"),"unicorn":("#fce7f3","#831843")}
            for b in blocks:
                n=regex_ex("NAME",b); st=regex_ex("STAGE",b); sz=regex_ex("SIZE",b)
                do=regex_ex("DOMAIN",b); wj=regex_ex("WHY_JOIN",b)
                sc=stage_colors.get(st.lower(),("#f1f5f9","#334155"))
                html += card_wrap(
                    title_div(f"🚀 {n}") +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(st,sc[0],sc[1])}{badge(f"👥 {sz}","#ecfdf5","#065f46")}{badge(f"🏷 {do}","#e0e7ff","#1e1b4b")}</div>' +
                    body_div(f"💡 {wj}")
                )

    j = re.search(r"JOBS_SECTION:(.*?)(?:TRENDS_SECTION:|$)", raw, re.DOTALL)
    if j:
        blocks = re.findall(r"JOB_START(.*?)JOB_END", j.group(1), re.DOTALL)
        if blocks:
            html += sec_title(f"💼 Live Job Openings ({len(blocks)} found)")
            for b in blocks:
                ti=regex_ex("TITLE",b); co=regex_ex("COMPANY",b); lo=regex_ex("LOCATION",b) or "Not specified"
                jt=regex_ex("TYPE",b) or "Full-time"; de=regex_ex("DESCRIPTION",b); li=regex_ex("LINK",b)
                tbg="#dcfce7" if "full" in jt.lower() else "#fef9c3"
                tcl="#14532d" if "full" in jt.lower() else "#713f12"
                html += card_wrap(
                    title_div(ti) +
                    f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'
                    f'{badge(f"🏛 {co}","#ede9fe","#4c1d95")}{badge(f"📍 {lo}","#ecfdf5","#065f46")}{badge(jt,tbg,tcl)}</div>' +
                    body_div(de) + apply_link(li)
                )

    t = re.search(r"TRENDS_SECTION:(.*?)(?:DOMAIN_SECTION:|$)", raw, re.DOTALL)
    if t:
        lines = [l.strip().lstrip("-•*").strip() for l in t.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #c7d0f8;font-size:0.9rem !important;color:#1a1a2e !important;display:flex;gap:8px"><span style="color:#6366f1;flex-shrink:0">▶</span><span style="color:#1a1a2e !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#eef1ff !important;border-left:4px solid #6366f1;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("📈 Trending Roles")}{items}</div>'

    d = re.search(r"DOMAIN_SECTION:(.*?)$", raw, re.DOTALL)
    if d:
        lines = [l.strip().lstrip("-•*").strip() for l in d.group(1).splitlines() if l.strip().lstrip("-•*").strip()]
        items = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #bbf7d0;font-size:0.9rem !important;color:#14532d !important;display:flex;gap:8px"><span style="color:#22c55e;flex-shrink:0">✦</span><span style="color:#14532d !important">{l}</span></div>' for l in lines)
        html += f'<div style="background:#ecfdf5 !important;border-left:4px solid #22c55e;border-radius:10px;padding:20px 24px;margin-bottom:24px">{sec_title("🌍 Domain Insights")}{items}</div>'

    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent5(domain, experience, location):
    if not domain.strip():
        return error_html("Please enter a domain.")
    try:
        r = get_agent5().invoke({"messages": [{"role": "user", "content": f"Top startups, jobs, trends for {domain} — Experience: {experience}, Location: {location or 'India'}"}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent5(raw)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# AGENT 6 — Skill Comparison Agent
# ==========================================

_agent6 = None

def get_agent6():
    global _agent6
    if _agent6:
        return _agent6

    model = get_model()
    serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)

    @tool
    def jobs_skill1_a6(skill: str, location: str) -> dict:
        """Fetch live jobs for skill 1."""
        jobs = fetch_jobs_rapidapi(f"{skill} developer jobs in {location}")
        return {"count": len(jobs), "samples": [{"title": j.get("job_title",""), "company": j.get("employer_name",""), "location": j.get("job_city","India")} for j in jobs[:5]]}

    @tool
    def jobs_skill2_a6(skill: str, location: str) -> dict:
        """Fetch live jobs for skill 2."""
        jobs = fetch_jobs_rapidapi(f"{skill} developer jobs in {location}")
        return {"count": len(jobs), "samples": [{"title": j.get("job_title",""), "company": j.get("employer_name",""), "location": j.get("job_city","India")} for j in jobs[:5]]}

    _agent6 = create_agent(
        model=model,
        tools=[
            Tool(name="skill1_search", func=serper.run, description="Search demand, salary, trends for skill 1."),
            Tool(name="skill2_search", func=serper.run, description="Search demand, salary, trends for skill 2."),
            Tool(name="comparison_search", func=serper.run, description="Search direct comparison between two skills."),
            jobs_skill1_a6, jobs_skill2_a6,
        ],
        system_prompt=(
            "You are a Skill Comparison assistant. Be strictly neutral.\n"
            "Structure your response EXACTLY like this:\n\n"
            "OVERVIEW_SECTION:\nSKILL1_OVERVIEW: [2-3 sentences]\nSKILL2_OVERVIEW: [2-3 sentences]\n\n"
            "COMPARISON_SECTION:\n"
            + "".join(f"METRIC_START\nMETRIC: {m}\nSKILL1_VALUE: [value]\nSKILL2_VALUE: [value]\nWINNER: [Skill1/Skill2/Tie]\nMETRIC_END\n" for m in ["Job Demand","Average Salary","Learning Curve","Future Scope","Community & Ecosystem","Freelance Opportunities","Enterprise Adoption"]) +
            "\nJOBS_SECTION:\nSKILL1_COUNT: [number]\nSKILL2_COUNT: [number]\n"
            "SKILL1_SAMPLES:\n- [title] — [company] — [location]\nSKILL2_SAMPLES:\n- [title] — [company] — [location]\n\n"
            "VERDICT_SECTION:\nOVERALL_WINNER: [skill or Depends]\nCHOOSE_SKILL1_IF: [scenario]\n"
            "CHOOSE_SKILL2_IF: [scenario]\nREASON: [2-3 sentences]\n\nNo markdown. Follow strictly."
        )
    )
    return _agent6

def format_agent6(raw, skill1, skill2):
    s1 = skill1.strip() or "Skill 1"
    s2 = skill2.strip() or "Skill 2"
    html = ""

    o = re.search(r"OVERVIEW_SECTION:(.*?)(?:COMPARISON_SECTION:|$)", raw, re.DOTALL)
    if o:
        ov1 = re.search(r"SKILL1_OVERVIEW:\s*(.+)", o.group(1))
        ov2 = re.search(r"SKILL2_OVERVIEW:\s*(.+)", o.group(1))
        t1 = ov1.group(1).strip() if ov1 else ""; t2 = ov2.group(1).strip() if ov2 else ""
        if t1 or t2:
            html += sec_title("📊 Overview")
            html += f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px"><div style="background:#eef1ff !important;border-left:4px solid #6366f1;border-radius:10px;padding:16px 20px"><div style="font-size:0.95rem !important;font-weight:700 !important;color:#1e1b4b !important;margin-bottom:8px">⚡ {s1}</div><div style="font-size:0.85rem !important;color:#1a1a2e !important;line-height:1.6">{t1}</div></div><div style="background:#fdf4ff !important;border-left:4px solid #a855f7;border-radius:10px;padding:16px 20px"><div style="font-size:0.95rem !important;font-weight:700 !important;color:#4c1d95 !important;margin-bottom:8px">⚡ {s2}</div><div style="font-size:0.85rem !important;color:#1a1a2e !important;line-height:1.6">{t2}</div></div></div>'

    c = re.search(r"COMPARISON_SECTION:(.*?)(?:JOBS_SECTION:|$)", raw, re.DOTALL)
    if c:
        metrics = re.findall(r"METRIC_START(.*?)METRIC_END", c.group(1), re.DOTALL)
        if metrics:
            html += sec_title("📋 Skill Comparison")
            html += f'<div style="background:#ffffff !important;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,0.06)"><div style="display:grid;grid-template-columns:2fr 2fr 2fr 1.2fr;background:#1e1b4b !important;padding:12px 16px;gap:8px"><div style="font-size:0.82rem !important;font-weight:700 !important;color:#fff !important">Metric</div><div style="font-size:0.82rem !important;font-weight:700 !important;color:#818cf8 !important">⚡ {s1}</div><div style="font-size:0.82rem !important;font-weight:700 !important;color:#c084fc !important">⚡ {s2}</div><div style="font-size:0.82rem !important;font-weight:700 !important;color:#fff !important">Winner</div></div>'
            for i, m in enumerate(metrics):
                me=regex_ex("METRIC",m); v1=regex_ex("SKILL1_VALUE",m); v2=regex_ex("SKILL2_VALUE",m); wi=regex_ex("WINNER",m)
                if s1.lower() in wi.lower(): wb = badge(f"✅ {s1}","#dcfce7","#14532d")
                elif s2.lower() in wi.lower(): wb = badge(f"✅ {s2}","#ede9fe","#4c1d95")
                else: wb = badge("🤝 Tie","#f1f5f9","#334155")
                rbg = "#f9fafb" if i%2==0 else "#ffffff"
                html += f'<div style="display:grid;grid-template-columns:2fr 2fr 2fr 1.2fr;background:{rbg} !important;padding:12px 16px;border-top:1px solid #f1f5f9;gap:8px;align-items:center"><div style="font-size:0.85rem !important;font-weight:600 !important;color:#111111 !important">{me}</div><div style="font-size:0.83rem !important;color:#1e1b4b !important">{v1}</div><div style="font-size:0.83rem !important;color:#4c1d95 !important">{v2}</div><div>{wb}</div></div>'
            html += "</div>"

    j = re.search(r"JOBS_SECTION:(.*?)(?:VERDICT_SECTION:|$)", raw, re.DOTALL)
    if j:
        jt = j.group(1)
        c1 = re.search(r"SKILL1_COUNT:\s*(.+)", jt); c2 = re.search(r"SKILL2_COUNT:\s*(.+)", jt)
        cnt1 = c1.group(1).strip() if c1 else "—"; cnt2 = c2.group(1).strip() if c2 else "—"
        sm1 = re.search(r"SKILL1_SAMPLES:(.*?)(?:SKILL2_SAMPLES:|$)", jt, re.DOTALL)
        sm2 = re.search(r"SKILL2_SAMPLES:(.*?)$", jt, re.DOTALL)
        def ps(t): return [l.strip().lstrip("-•*").strip() for l in (t or "").splitlines() if l.strip().lstrip("-•*").strip()]
        s1s = ps(sm1.group(1) if sm1 else ""); s2s = ps(sm2.group(1) if sm2 else "")
        html += sec_title("💼 Live Job Counts")
        s1_items = "".join(f'<div style="font-size:0.8rem !important;color:#374151 !important;padding:4px 0;border-bottom:1px solid #f1f5f9">• {s}</div>' for s in s1s)
        s2_items = "".join(f'<div style="font-size:0.8rem !important;color:#374151 !important;padding:4px 0;border-bottom:1px solid #f1f5f9">• {s}</div>' for s in s2s)
        html += (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px">'
            f'<div style="background:#ffffff !important;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px">'
            f'<div style="font-size:0.9rem !important;font-weight:700 !important;color:#1e1b4b !important;margin-bottom:6px">⚡ {s1}</div>'
            f'<div style="font-size:1.8rem !important;font-weight:800 !important;color:#6366f1 !important;margin-bottom:10px">'
            f'{cnt1}<span style="font-size:0.8rem;color:#6b7280;font-weight:400"> jobs found</span></div>'
            f'{s1_items}</div>'
            f'<div style="background:#ffffff !important;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px">'
            f'<div style="font-size:0.9rem !important;font-weight:700 !important;color:#4c1d95 !important;margin-bottom:6px">⚡ {s2}</div>'
            f'<div style="font-size:1.8rem !important;font-weight:800 !important;color:#a855f7 !important;margin-bottom:10px">'
            f'{cnt2}<span style="font-size:0.8rem;color:#6b7280;font-weight:400"> jobs found</span></div>'
            f'{s2_items}</div></div>'
        )

    v = re.search(r"VERDICT_SECTION:(.*?)$", raw, re.DOTALL)
    if v:
        vt=v.group(1); wi=regex_ex("OVERALL_WINNER",vt); cs1=regex_ex("CHOOSE_SKILL1_IF",vt)
        cs2=regex_ex("CHOOSE_SKILL2_IF",vt); re_=regex_ex("REASON",vt)
        it = "depend" in wi.lower() or "tie" in wi.lower()
        wbg="#fef9c3" if it else "#dcfce7"; wcl="#713f12" if it else "#14532d"
        wic="🤝" if it else "🏆"; wbord="#f59e0b" if it else "#22c55e"
        html += sec_title("🏆 Verdict & Recommendation")
        html += f'<div style="background:{wbg} !important;border-left:4px solid {wbord};border-radius:10px;padding:16px 20px;margin-bottom:16px"><div style="font-size:1rem !important;font-weight:800 !important;color:{wcl} !important;margin-bottom:6px">{wic} Overall Winner: {wi}</div><div style="font-size:0.85rem !important;color:{wcl} !important;line-height:1.6">{re_}</div></div>'
        html += f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px"><div style="background:#eef1ff !important;border-radius:10px;padding:16px 20px"><div style="font-size:0.85rem !important;font-weight:700 !important;color:#1e1b4b !important;margin-bottom:6px">✅ Choose {s1} if...</div><div style="font-size:0.83rem !important;color:#1a1a2e !important;line-height:1.5">{cs1}</div></div><div style="background:#fdf4ff !important;border-radius:10px;padding:16px 20px"><div style="font-size:0.85rem !important;font-weight:700 !important;color:#4c1d95 !important;margin-bottom:6px">✅ Choose {s2} if...</div><div style="font-size:0.83rem !important;color:#1a1a2e !important;line-height:1.5">{cs2}</div></div></div>'

    return wrap_html(html) if html else wrap_html(fallback_html(raw))

def run_agent6(skill1, skill2, goal):
    if not skill1.strip() or not skill2.strip():
        return error_html("Please enter both skills.")
    try:
        r = get_agent6().invoke({"messages": [{"role": "user", "content": f"Compare {skill1} vs {skill2} — Goal: {goal}, Location: India"}]})
        raw = r["messages"][-1].content
        if isinstance(raw, list): raw = " ".join(b.get("text","") if isinstance(b,dict) else str(b) for b in raw).strip()
        return format_agent6(raw, skill1, skill2)
    except Exception as e:
        return error_html(str(e))

# ==========================================
# GRADIO UI — Tabbed Interface
# ==========================================

css = """
    body { background: #f8f9fc; }
    footer { display: none !important; }
    .tab-nav button { font-weight: 600 !important; }
    h1, h2, h3, h4, h5, h6 {
        color: #1e1b4b !important;
        font-weight: bold !important;
    }
"""

theme = gr.themes.Soft(
    primary_hue="indigo",
    font=[gr.themes.GoogleFont("DM Sans"), "sans-serif"],
)

with gr.Blocks(theme=theme, css=css) as demo:

    gr.HTML("""
    <div style="text-align:center;padding:24px 0 8px">
        <h1 style="font-size:2.2rem;font-weight:900;color:#1e1b4b;margin-bottom:6px">
            🧠 Career AI Platform
        </h1>
        <p style="color:#6b7280;font-size:1rem">
            6 AI agents to supercharge your career — all in one place.
        </p>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Skill to Career Mapper ──────────────────────────────
        with gr.TabItem("🎯 Skill Mapper"):
            gr.Markdown("### Find industry demand for your skill and matching job openings.")
            with gr.Row():
                a1_skill = gr.Textbox(label="Skill", placeholder="e.g. Machine Learning, React...", scale=2)
                a1_loc   = gr.Textbox(label="Location", placeholder="e.g. Bangalore (default: India)", scale=1)
            a1_custom = gr.Textbox(label="Custom Query (optional)", placeholder="e.g. Demand for GenAI in startups...", lines=2)
            a1_btn    = gr.Button("🔍 Find Careers", variant="primary", size="lg")
            a1_out    = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Results will appear here.</div>")
            gr.Examples([["Machine Learning","Bangalore",""],["React","India",""],["","","GenAI demand in startups and remote jobs"]], inputs=[a1_skill,a1_loc,a1_custom])
            a1_btn.click(fn=run_agent1, inputs=[a1_skill,a1_loc,a1_custom], outputs=a1_out, show_progress="full")

        # ── Tab 2: Interview Prep ──────────────────────────────────────
        with gr.TabItem("🎤 Interview Prep"):
            gr.Markdown("### Get 20 interview questions, prep tips, and resources for any role.")
            with gr.Row():
                a2_role  = gr.Textbox(label="Role", placeholder="e.g. Data Analyst, Backend Engineer...", scale=3)
                a2_level = gr.Dropdown(label="Level", choices=["Fresher","Mid-level","Senior"], value="Fresher", scale=1)
                a2_round = gr.Dropdown(label="Round", choices=["Technical","HR","System Design","Behavioural"], value="Technical", scale=1)
            a2_btn = gr.Button("🔍 Generate Prep Guide", variant="primary", size="lg")
            a2_out = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Results will appear here.</div>")
            gr.Examples([["Data Analyst","Fresher","Technical"],["Backend Engineer","Mid-level","System Design"],["Product Manager","Senior","Behavioural"]], inputs=[a2_role,a2_level,a2_round])
            a2_btn.click(fn=run_agent2, inputs=[a2_role,a2_level,a2_round], outputs=a2_out, show_progress="full")

        # ── Tab 3: Salary Insights ─────────────────────────────────────
        with gr.TabItem("💰 Salary Insights"):
            gr.Markdown("### Get salary ranges, top paying companies, and city-wise comparisons.")
            with gr.Row():
                a3_job = gr.Textbox(label="Job Title", placeholder="e.g. Full Stack Developer, Data Scientist...", scale=3)
                a3_loc = gr.Dropdown(label="Location", choices=["India","Bangalore","Hyderabad","Mumbai","Pune","Chennai","Delhi","Remote"], value="India", scale=1)
            a3_btn = gr.Button("🔍 Get Salary Insights", variant="primary", size="lg")
            a3_out = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Results will appear here.</div>")
            gr.Examples([["Full Stack Developer","Bangalore"],["Data Scientist","Hyderabad"],["ML Engineer","India"]], inputs=[a3_job,a3_loc])
            a3_btn.click(fn=run_agent3, inputs=[a3_job,a3_loc], outputs=a3_out, show_progress="full")

        # ── Tab 4: Course Finder ───────────────────────────────────────
        with gr.TabItem("📚 Course Finder"):
            gr.Markdown("### Find free courses, certifications, roadmaps and top platforms for any skill.")
            with gr.Row():
                a4_skill = gr.Textbox(label="Skill", placeholder="e.g. Gen AI, React, Data Science...", scale=3)
                a4_level = gr.Dropdown(label="Your Level", choices=["Beginner","Intermediate","Advanced"], value="Beginner", scale=1)
            a4_btn = gr.Button("🔍 Find Courses", variant="primary", size="lg")
            a4_out = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Results will appear here.</div>")
            gr.Examples([["Gen AI","Beginner"],["React","Intermediate"],["Cybersecurity","Beginner"]], inputs=[a4_skill,a4_level])
            a4_btn.click(fn=run_agent4, inputs=[a4_skill,a4_level], outputs=a4_out, show_progress="full")

        # ── Tab 5: Startup Jobs ────────────────────────────────────────
        with gr.TabItem("🚀 Startup Jobs"):
            gr.Markdown("### Discover top startups, live job openings, and hiring trends in any domain.")
            with gr.Row():
                a5_domain = gr.Textbox(label="Domain", placeholder="e.g. FinTech, HealthTech, EdTech, AI...", scale=3)
                a5_exp    = gr.Dropdown(label="Experience", choices=["Fresher","Mid-level","Senior"], value="Fresher", scale=1)
                a5_loc    = gr.Dropdown(label="Location", choices=["India","Bangalore","Hyderabad","Mumbai","Pune","Delhi","Remote"], value="India", scale=1)
            a5_btn = gr.Button("🔍 Find Startup Jobs", variant="primary", size="lg")
            a5_out = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Results will appear here.</div>")
            gr.Examples([["FinTech","Fresher","Bangalore"],["HealthTech","Mid-level","Hyderabad"],["AI","Fresher","India"]], inputs=[a5_domain,a5_exp,a5_loc])
            a5_btn.click(fn=run_agent5, inputs=[a5_domain,a5_exp,a5_loc], outputs=a5_out, show_progress="full")

        # ── Tab 6: Skill Comparison ────────────────────────────────────
        with gr.TabItem("⚔️ Skill Compare"):
            gr.Markdown("### Compare two skills side-by-side — demand, salary, jobs, future scope.")
            with gr.Row():
                a6_s1   = gr.Textbox(label="Skill 1", placeholder="e.g. React", scale=2)
                gr.HTML('<div style="display:flex;align-items:center;justify-content:center;font-size:1.5rem;font-weight:800;color:#6366f1;padding-top:24px">vs</div>')
                a6_s2   = gr.Textbox(label="Skill 2", placeholder="e.g. Angular", scale=2)
                a6_goal = gr.Dropdown(label="Your Goal", choices=["Get a Job","Freelancing","Startup","Enterprise Career"], value="Get a Job", scale=1)
            a6_btn = gr.Button("⚔️ Compare Skills", variant="primary", size="lg")
            a6_out = gr.HTML(value="<div style='color:#9ca3af;padding:40px;text-align:center'>Comparison results will appear here.</div>")
            gr.Examples([["React","Angular","Get a Job"],["Python","JavaScript","Freelancing"],["AWS","Azure","Enterprise Career"]], inputs=[a6_s1,a6_s2,a6_goal])
            a6_btn.click(fn=run_agent6, inputs=[a6_s1,a6_s2,a6_goal], outputs=a6_out, show_progress="full")

if __name__ == "__main__":
    demo.launch(share=False)