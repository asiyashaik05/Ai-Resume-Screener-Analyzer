import streamlit as st
import fitz, pdfplumber, docx, re
from PIL import Image
import pytesseract
from io import BytesIO
from fpdf import FPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------- Utility ---------------- #
def clean_text(s):
    if not s: return ""
    s = s.replace("\xa0", " ").replace("•", "-")
    s = re.sub(r"[\u200b-\u200d\uFEFF]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def sanitize_for_pdf(s):
    s = re.sub(r"[^\x00-\x7F]+","", s)
    return s.strip()

# ---------------- Extraction ---------------- #
def extract_text_from_pdf(file):
    file.seek(0)
    try:
        data = file.read()
        with fitz.open(stream=data, filetype="pdf") as pdf:
            text = " ".join([p.get_text("text") for p in pdf])
            if len(text) > 20:
                return clean_text(text)
    except:
        pass
    try:
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            return clean_text(text)
    except:
        return ""

def extract_text_from_docx(file):
    doc = docx.Document(file)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return clean_text("\n".join(parts))

def extract_text_from_image(file):
    img = Image.open(file)
    return clean_text(pytesseract.image_to_string(img))

# ---------------- Skills ---------------- #
SKILLS = {
    "html":"frontend","css":"frontend","javascript":"frontend","typescript":"frontend",
    "react":"frontend","angular":"frontend","vue":"frontend","bootstrap":"frontend",
    "nodejs":"backend","express":"backend","django":"backend","flask":"backend",
    "java":"backend","springboot":"backend","python":"backend","php":"backend",
    "mysql":"database","postgresql":"database","mongodb":"database","redis":"database",
    "aws":"cloud","azure":"cloud","gcp":"cloud","docker":"cloud","kubernetes":"cloud",
    "git":"tools","github":"tools","figma":"design","ux":"design","ui":"design","sketch":"design",
    "communication":"soft","teamwork":"soft","leadership":"soft"
}

ROLES = {
    "Full Stack Developer":{"html","css","javascript","react","nodejs","mysql"},
    "Frontend Developer":{"html","css","javascript","react","angular"},
    "Backend Developer":{"nodejs","express","java","springboot","mysql"},
    "MERN Stack Developer":{"react","nodejs","mongodb"},
    "Python Developer":{"python","django","flask"},
    "DevOps Engineer":{"aws","docker","kubernetes"},
    "UI/UX Designer":{"figma","ux","ui","sketch"}
}

ROLE_DESCRIPTIONS = {
    "Full Stack Developer":"Builds and maintains both frontend and backend systems.",
    "Frontend Developer":"Creates intuitive and responsive user interfaces.",
    "Backend Developer":"Designs APIs, databases, and server logic.",
    "MERN Stack Developer":"Develops full-stack JS applications using MongoDB, Express, React, Node.js.",
    "Python Developer":"Develops backend systems and automation tools in Python.",
    "DevOps Engineer":"Manages CI/CD, infrastructure, and cloud deployments.",
    "UI/UX Designer":"Designs engaging digital experiences using tools like Figma or Sketch."
}

# ---------------- Core Logic ---------------- #
def detect_skills(text):
    txt = text.lower()
    return {s for s in SKILLS if re.search(rf"\b{s}\b", txt)}

def semantic_similarity(a, b):
    try:
        vect = TfidfVectorizer(stop_words="english").fit([a,b])
        X = vect.transform([a,b])
        return float(cosine_similarity(X[0], X[1])[0][0])*100
    except:
        return 0.0

# ---------------- AI Suggestions (Skill-Aware) ---------------- #
def generate_dynamic_suggestions(matched, missing, resume, jd):
    suggestions = []
    jd_lower = jd.lower()
    res_lower = resume.lower()

    # 1️⃣ Missing skill-based
    for skill in missing[:3]:
        if SKILLS.get(skill) == "frontend":
            suggestions.append(f"Add a frontend project highlighting your experience with {skill} or responsive UI design.")
        elif SKILLS.get(skill) == "backend":
            suggestions.append(f"Include backend or API integration examples using {skill}.")
        elif SKILLS.get(skill) == "database":
            suggestions.append(f"Add a project showcasing database operations or schema design using {skill}.")
        elif SKILLS.get(skill) == "cloud":
            suggestions.append(f"Show deployment or CI/CD experience using {skill}.")
        elif SKILLS.get(skill) == "soft":
            suggestions.append(f"Add teamwork or communication achievements under soft skills.")

    # 2️⃣ Resume content-based
    if "project" not in res_lower:
        suggestions.append("Include a 'Projects' section to show real-world applications of your skills.")
    if "github" not in res_lower:
        suggestions.append("Add a GitHub or portfolio link to validate your code quality.")
    if "team" not in res_lower:
        suggestions.append("Mention teamwork or leadership in your experience section.")

    # 3️⃣ Job description context
    if "frontend" in jd_lower and not any(k in res_lower for k in ["html","css","react","angular"]):
        suggestions.append("Highlight any UI or front-end work you've done, emphasizing visual design or interactivity.")
    if "backend" in jd_lower and not any(k in res_lower for k in ["nodejs","api","flask","django"]):
        suggestions.append("Add backend experience, such as REST API creation or microservice architecture.")

    return list(dict.fromkeys(suggestions))[:5]

# ---------------- Roles ---------------- #
def recommend_roles(resume_skills):
    roles = []
    for r, req in ROLES.items():
        matched = list(resume_skills & req)
        score = round((len(matched)/len(req))*100, 1)
        if score > 0:
            roles.append((r, score, matched))
    return sorted(roles, key=lambda x:x[1], reverse=True)[:4]

# ---------------- PDF Generator ---------------- #
def generate_pdf(score, matched, missing, suggestions, roles, summary):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,10,"AI Resume Analyzer Report",ln=True,align="C")
    pdf.set_font("Helvetica","",12)
    pdf.cell(0,8,f"Match Score: {score}%",ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica","B",12)
    pdf.cell(95,8,"Matched Skills",ln=False)
    pdf.cell(0,8,"Missing Skills",ln=True)
    pdf.set_font("Helvetica","",11)
    for i in range(max(len(matched),len(missing))):
        left = matched[i] if i<len(matched) else ""
        right = missing[i] if i<len(missing) else ""
        pdf.cell(95,7,f"- {left}",ln=False)
        pdf.cell(0,7,f"- {right}",ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica","B",12)
    pdf.cell(0,8,"AI Suggestions",ln=True)
    pdf.set_font("Helvetica","",11)
    for s in suggestions:
        pdf.multi_cell(0,7,"- "+sanitize_for_pdf(s))

    pdf.ln(4)
    pdf.set_font("Helvetica","B",12)
    pdf.cell(0,8,"Recommended Roles",ln=True)
    pdf.set_font("Helvetica","",11)
    for r,sc,m in roles:
        desc=ROLE_DESCRIPTIONS.get(r,"")
        pdf.multi_cell(0,7,f"- {r} ({sc}% match): {desc}")

    pdf.ln(4)
    pdf.set_font("Helvetica","B",12)
    pdf.cell(0,8,"Summary",ln=True)
    pdf.set_font("Helvetica","",11)
    pdf.multi_cell(0,7,sanitize_for_pdf(summary))

    out=pdf.output(dest="S").encode("latin-1","ignore")
    buf=BytesIO(out);buf.seek(0)
    return buf

# ---------------- Streamlit UI ---------------- #
st.set_page_config(page_title="AI Resume Screener v5.7",layout="centered")
st.markdown("<h1 style='text-align:center;color:#0d6efd;'>AI Resume Screener & Analyzer</h1>",unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:gray;'>Smart AI tool that compares your resume and job description to provide ATS-style insights.</p>",unsafe_allow_html=True)

resume=st.file_uploader("📄 Upload Resume",type=["pdf","docx","png","jpg","jpeg","txt"])
jd=st.text_area("🧾 Job Description",height=260)
if st.button("🔍 Analyze Resume"):
    if not resume or not jd.strip():
        st.warning("Please upload a resume and paste a job description.")
    else:
        with st.spinner("Analyzing your resume..."):
            name=resume.name.lower()
            if name.endswith(".pdf"): text=extract_text_from_pdf(resume)
            elif name.endswith(".docx"): text=extract_text_from_docx(resume)
            elif name.endswith((".png",".jpg",".jpeg")): text=extract_text_from_image(resume)
            else:
                resume.seek(0);text=resume.read().decode("utf-8",errors="ignore")

            resume_skills=detect_skills(text)
            jd_skills=detect_skills(jd)
            matched=sorted(list(resume_skills&jd_skills))
            missing=sorted(list(jd_skills-resume_skills))
            overlap=len(matched)/max(1,len(jd_skills))*100
            sem=semantic_similarity(text,jd)
            score=round(0.85*overlap+0.15*sem,2)

        # Label
        if score<30: color,label="red","❌ Needs Improvement"
        elif score<60: color,label="#f0ad4e","⚠ Average Fit"
        else: color,label="green","✅ Good Fit"

        st.markdown(f"<h3 style='color:{color};'>Match Score: {score}% ({label})</h3>",unsafe_allow_html=True)
        st.progress(min(score/100,1.0))

        # Matched / Missing
        st.markdown("<p style='color:gray;'>Following skills detected after analyzing your resume and job description:</p>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### ✅ Matched Skills")
            for s in matched: st.write(f"- {s}")
            if not matched: st.write("- None detected.")
        with c2:
            st.markdown("#### ⚠ Missing Skills")
            for s in missing: st.write(f"- {s}")
            if not missing: st.write("- None detected.")

        # Suggestions
        st.markdown("### 💡 AI Suggestions to Improve Your Match")
        suggestions=generate_dynamic_suggestions(matched,missing,text,jd)
        for s in suggestions: st.write("- "+s)

        # Roles
        st.markdown("### 🧭 Recommended Roles (based on your resume)")
        roles=recommend_roles(resume_skills)
        for r,sc,m in roles:
            st.write(f"- *{r} ({sc}% match)* — {ROLE_DESCRIPTIONS.get(r,'')}")

        # Summary
        summary=(
            f"Your resume currently matches {len(matched)} of {len(jd_skills)} required skills, scoring {score}%. "
            f"Strong areas include {', '.join(matched) if matched else 'general proficiencies'} while improvement is needed in {', '.join(missing) if missing else 'presentation clarity'}. "
            "Add measurable project outcomes and deployment experience to strengthen your profile. "
            f"Based on this analysis, your resume is {label.replace('✅','').replace('⚠','').replace('❌','').strip()} for this role."
        )
        st.markdown("### 📊 Summary")
        st.info(summary)

        pdf_buf=generate_pdf(score,matched,missing,suggestions,roles,summary)
        st.download_button("📥 Download PDF Report",data=pdf_buf,file_name="AI_Resume_Analyzer_Report_v5.7.pdf",mime="application/pdf")