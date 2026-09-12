import streamlit as st
import pandas as pd
import os
import datetime

try:
    from fpdf import FPDF
    HAS_FPDF = True
except:
    HAS_FPDF = False

# ---- DATABASE ----
try:
    import psycopg2
    DATABASE_URL = st.secrets["DATABASE_URL"] if "DATABASE_URL" in st.secrets else os.getenv("DATABASE_URL")
    def get_conn():
        return psycopg2.connect(DATABASE_URL)
    USE_POSTGRES = True
except:
    import sqlite3
    def get_conn():
        return sqlite3.connect("jawabu.db", check_same_thread=False)
    USE_POSTGRES = False

def init_db():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS students (id SERIAL PRIMARY KEY, name TEXT, reg_no TEXT UNIQUE, class TEXT, parent_phone TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS academics (id SERIAL PRIMARY KEY, reg_no TEXT, subject TEXT, score INT, grade TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS fees (id SERIAL PRIMARY KEY, reg_no TEXT, amount INT, date TEXT)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, reg_no TEXT UNIQUE, class TEXT, parent_phone TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, subject TEXT, score INT, grade TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS fees (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, amount INT, date TEXT)")
    conn.commit()
    conn.close()

init_db()
st.set_page_config(page_title="JAWABU SCHOOL", layout="wide")
st.title("🎓 JAWABU LEARNING CENTRE")
if USE_POSTGRES:
    st.success("✅ Permanent Database - Records will NOT disappear")
else:
    st.warning("⚠️ Temporary DB - Add DATABASE_URL in Secrets")

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Student Registration", "Academics", "Report Card - CBC Presentable", "Fees"])

if menu == "Dashboard":
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM students", conn)
    conn.close()
    st.metric("Total Students", len(df))
    st.dataframe(df)

elif menu == "Student Registration":
    st.subheader("Register New Student")
    with st.form("reg"):
        name = st.text_input("Full Name")
        reg_no = st.text_input("Reg No e.g. JAW/001")
        s_class = st.selectbox("Class", ["PP1","PP2","Grade 1","Grade 2","Grade 3","Grade 4","Grade 5","Grade 6","JSS"])
        phone = st.text_input("Parent Phone")
        submit = st.form_submit_button("Save Student")
        if submit and reg_no:
            try:
                conn = get_conn()
                c = conn.cursor()
                if USE_POSTGRES:
                    c.execute("INSERT INTO students (name, reg_no, class, parent_phone) VALUES (%s,%s,%s,%s)", (name, reg_no, s_class, phone))
                else:
                    c.execute("INSERT INTO students (name, reg_no, class, parent_phone) VALUES (?,?,?,?)", (name, reg_no, s_class, phone))
                conn.commit()
                conn.close()
                st.success(f"Saved {name}")
            except Exception as e:
                st.error(f"Error: {e}")

elif menu == "Academics":
    st.subheader("Enter Marks")
    with st.form("marks"):
        reg_no = st.text_input("Reg No")
        subject = st.text_input("Subject")
        score = st.number_input("Score", 0, 100)
        grade = st.selectbox("Grade", ["EE1","EE2","ME1","ME2","AE"])
        submit = st.form_submit_button("Save Marks")
        if submit:
            conn = get_conn()
            c = conn.cursor()
            if USE_POSTGRES:
                c.execute("INSERT INTO academics (reg_no, subject, score, grade) VALUES (%s,%s,%s,%s)", (reg_no, subject, score, grade))
            else:
                c.execute("INSERT INTO academics (reg_no, subject, score, grade) VALUES (?,?,?,?)", (reg_no, subject, score, grade))
            conn.commit()
            conn.close()
            st.success("Marks saved!")

elif menu == "Report Card - CBC Presentable":
    st.subheader("Report Card")
    reg_no = st.text_input("Enter Reg No")
    if reg_no:
        conn = get_conn()
        c = conn.cursor()
        if USE_POSTGRES:
            c.execute("SELECT * FROM students WHERE reg_no=%s", (reg_no,))
            student = c.fetchone()
            c.execute("SELECT subject, score, grade FROM academics WHERE reg_no=%s", (reg_no,))
            marks = c.fetchall()
        else:
            c.execute("SELECT * FROM students WHERE reg_no=?", (reg_no,))
            student = c.fetchone()
            c.execute("SELECT subject, score, grade FROM academics WHERE reg_no=?", (reg_no,))
            marks = c.fetchall()
        conn.close()
        if not student:
            st.error("Student not found!")
        elif not marks:
            st.warning("No marks found. Go to Academics first.")
        else:
            s_name = student[1]
            s_reg = student[2]
            s_class = student[3]
            st.markdown(f"### {s_name} | {s_reg} | {s_class}")
            df_marks = pd.DataFrame(marks, columns=["Subject","Score","Grade"])
            st.table(df_marks)
            if not HAS_FPDF:
                st.warning("Add fpdf2 to requirements.txt to enable DOWNLOAD button")
            else:
                def create_report_pdf():
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "JAWABU LEARNING CENTRE", ln=True, align="C")
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 8, "CBC COMPETENCY REPORT CARD", ln=True, align="C")
                    pdf.ln(10)
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 8, f"Name: {s_name}", ln=True)
                    pdf.cell(0, 8, f"Reg: {s_reg} | Class: {s_class} | Date: {datetime.date.today()}", ln=True)
                    pdf.ln(5)
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(70, 10, "Subject", border=1)
                    pdf.cell(40, 10, "Score", border=1)
                    pdf.cell(40, 10, "Grade", border=1, ln=True)
                    pdf.set_font("Arial", "", 11)
                    for subj, score, grade in marks:
                        pdf.cell(70, 10, str(subj), border=1)
                        pdf.cell(40, 10, str(score), border=1)
                        pdf.cell(40, 10, str(grade), border=1, ln=True)
                    return pdf.output(dest="S").encode("latin1")
                pdf_bytes = create_report_pdf()
                st.download_button(label="📥 DOWNLOAD REPORT CARD PDF", data=pdf_bytes, file_name=f"Report_{s_reg}.pdf", mime="application/pdf", use_container_width=True, type="primary")

elif menu == "Fees":
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM fees", conn)
    conn.close()
    st.dataframe(df)
