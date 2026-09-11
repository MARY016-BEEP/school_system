import streamlit as st
import pandas as pd
import datetime, os, json, sqlite3

st.set_page_config(page_title="JAWABU LEARNING CENTRE", page_icon="🏫", layout="wide")
st.markdown("""<style>
.stApp {background: #fff0f3;}
h1,h2,h3 {color: #ff4d7a!important;}
div[data-testid="stMetric"] {background:white; border:1px solid #ffe4e9; border-radius:20px; padding:10px;}
.stButton>button {background:#ff85a1; color:white; border-radius:12px; border:none; font-weight:bold;}
</style>""", unsafe_allow_html=True)

FEE_STRUCTURE = {"Play Group": 5000, "PP1": 7000, "PP2": 7000, "Grade 1": 10000, "Grade 2": 10000, "Grade 3": 10000, "Grade 4": 10000, "Grade 5": 10000, "Grade 6": 10000, "Grade 7": 12000, "Grade 8": 12000, "Grade 9": 12000}
CLASSES = list(FEE_STRUCTURE.keys())
SUBJECTS_MAP = {
    "Play Group": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "PP1": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "PP2": ["Language","Mathematical","Environmental","Psychomotor & Creative","Religious"],
    "Grade 1": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene"],
    "Grade 2": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene"],
    "Grade 3": ["Mathematics","English","Kiswahili","Environmental","Creative Art","Hygiene & Nutrition"],
    "Grade 4": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 5": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 6": ["Mathematics","English","Kiswahili","Science & Tech","Social Studies","CRE","Agriculture","Creative Arts"],
    "Grade 7": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"],
    "Grade 8": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"],
    "Grade 9": ["Mathematics","English","Kiswahili","Integrated Science","Social Studies","CRE","Agriculture","Pre-Technical","Business"]
}

@st.cache_resource
def get_conn():
    return sqlite3.connect('jawabu.db', check_same_thread=False)
conn = get_conn()
cur = conn.cursor()

# --- TABLES ---
cur.execute("CREATE TABLE IF NOT EXISTS students (reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)")
cur.execute("CREATE TABLE IF NOT EXISTS mpesa_trans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, reg_no TEXT, mpesa_code TEXT, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, amount INT, description TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, term TEXT, exam_type TEXT, subjects_json TEXT, total INT, mean REAL, grade TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, active INT, created_by TEXT, created_at TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, username TEXT, role TEXT, action TEXT, details TEXT)")

# Default users if empty
if pd.read_sql("SELECT * FROM users", conn).empty:
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("admin","Jawabu@2026","DIRECTOR",1,"system",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("accountant","Acc@2026","ACCOUNTANT",1,"admin",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("teacher","Teach@2026","TEACHER",1,"admin",str(datetime.datetime.now())))
    conn.commit()

def log_action(username, role, action, details):
    cur.execute("INSERT INTO audit_logs (timestamp,username,role,action,details) VALUES (?,?,?,?,?)", (str(datetime.datetime.now()), username, role, action, details))
    conn.commit()

# --- LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center'>🏫 JAWABU LEARNING CENTRE</h1>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            u=st.text_input("Username")
            p=st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True):
                df_user = pd.read_sql(f"SELECT * FROM users WHERE username='{u}' AND password='{p}'", conn)
                if not df_user.empty and df_user.iloc[0]['active']==1:
                    st.session_state.logged_in=True
                    st.session_state.username=u
                    st.session_state.role=df_user.iloc[0]['role']
                    log_action(u, df_user.iloc[0]['role'], "LOGIN", "Logged in")
                    st.rerun()
                elif not df_user.empty and df_user.iloc[0]['active']==0:
                    st.error("Account DISABLED by Director. Contact Director.")
                else:
                    st.error("Wrong credentials")
    st.stop()

username = st.session_state.username
role = st.session_state.role

# --- SIDEBAR MENU BY ROLE ---
st.sidebar.markdown(f"### 🏫 JAWABU\n**User:** {username}\n**Role:** {role}")
if role=="ACCOUNTANT":
    menu_options = ["Admissions","Finance - Auto STK","Expenses","Fee Defaulters & Reports"]
elif role=="TEACHER":
    menu_options = ["Academics CBC","Report Cards"]
else: # DIRECTOR
    menu_options = ["Director Dashboard","Admissions","Finance - Auto STK","Expenses","Academics CBC","Report Cards","Fee Defaulters & Reports","User Management","Audit Logs"]

menu = st.sidebar.radio("MENU", menu_options)
if st.sidebar.button("Logout"):
    log_action(username, role, "LOGOUT", "Logged out")
    st.session_state.logged_in=False; st.rerun()

# --- FUNCTIONS ---
def show_student_auto(reg_input):
    if reg_input:
        df = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_input}'", conn)
        if not df.empty:
            s=df.iloc[0]
            st.success(f"✅ **{s['name']}** | Class: **{s['class']}** | Balance: Ksh {s['balance']} | Parent: {s['parent_phone']}")
            return s
        else:
            st.error("Reg No not found"); return None
    return None

# --- PAGES ---

if menu=="Director Dashboard":
    st.title("Director Dashboard - Profit = Collected - Expenses")
    df_exp = pd.read_sql("SELECT * FROM expenses", conn)
    df_mp = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Collected", f"Ksh {df_mp['amount'].sum() if not df_mp.empty else 0}")
    c2.metric("Expenses", f"Ksh {df_exp['amount'].sum() if not df_exp.empty else 0}")
    c3.metric("PROFIT", f"Ksh {(df_mp['amount'].sum() if not df_mp.empty else 0)-(df_exp['amount'].sum() if not df_exp.empty else 0)}")
    c4.metric("Students", pd.read_sql("SELECT * FROM students", conn).shape[0])
    st.dataframe(df_mp, use_container_width=True)

elif menu=="Admissions":
    st.subheader("Admissions")
    with st.form("admit"):
        c1,c2,c3=st.columns(3)
        s_name=c1.text_input("Student Name"); p_name=c2.text_input("Parent Name"); p_phone=c3.text_input("Parent Phone 2547...")
        s_class=c1.selectbox("Class", CLASSES); gender=c2.selectbox("Gender",["Male","Female"]); dob=c3.date_input("DOB")
        if st.form_submit_button("Admit"):
            fee=FEE_STRUCTURE[s_class]; cnt=pd.read_sql("SELECT * FROM students", conn).shape[0]; reg=f"JLC/{cnt+1:04d}/{datetime.date.today().year%100}"
            cur.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (reg,s_name,p_name,p_phone,s_class,gender,str(dob),"","",fee,0,fee,0)); conn.commit()
            log_action(username, role, "ADMISSION", f"Admitted {reg} {s_name} in {s_class}")
            st.success(f"Admitted {reg}")
    st.dataframe(pd.read_sql("SELECT reg_no,name,class,parent_phone,balance FROM students", conn), use_container_width=True)

elif menu=="Finance - Auto STK":
    st.subheader("Finance - Auto Reflect Class")
    reg_input = st.text_input("Enter Reg No", key="fin_reg")
    student = show_student_auto(reg_input)
    phone_auto = student['parent_phone'] if student is not None else ""
    with st.form("pay"):
        c1,c2=st.columns(2)
        amount=c1.number_input("Amount", min_value=1)
        phone=c2.text_input("Phone", value=phone_auto)
        if st.form_submit_button("📲 SEND STK & RECORD"):
            if student is None:
                st.error("Enter valid Reg No first")
            else:
                tuition=int(amount*0.8); transport=int(amount*0.15); library=amount-tuition-transport
                code=f"QAH{os.urandom(2).hex().upper()}"
                cur.execute("INSERT INTO mpesa_trans (date,reg_no,mpesa_code,amount,phone,tuition,transport,library,status,done_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (str(datetime.datetime.now()), reg_input, code, int(amount), phone, tuition, transport, library, "VERIFIED", username))
                cur.execute("UPDATE students SET paid=paid+?, balance=balance-? WHERE reg_no=?", (int(amount), int(amount), reg_input))
                conn.commit()
                log_action(username, role, "FINANCE PAYMENT", f"{reg_input} paid {amount} code {code}")
                st.success(f"Recorded {code}")
    st.dataframe(pd.read_sql("SELECT date,reg_no,mpesa_code,amount,done_by,status FROM mpesa_trans ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Expenses":
    st.subheader("Expenses")
    with st.form("exp"):
        c1,c2,c3=st.columns(3)
        t=c1.selectbox("Type",["Salary","Food","Books","Electricity","Wifi","Transport"])
        a=c2.number_input("Amount"); d=c3.text_input("Desc")
        if st.form_submit_button("Add Expense"):
            cur.execute("INSERT INTO expenses (date,type,amount,description,done_by) VALUES (?,?,?,?,?)", (str(datetime.date.today()),t,a,d,username)); conn.commit()
            log_action(username, role, "EXPENSE", f"Added {t} {a} - {d}")
            st.success("Added")
    st.dataframe(pd.read_sql("SELECT * FROM expenses ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Academics CBC":
    st.subheader("CBC - Auto Subjects by Class")
    reg_no_input = st.text_input("Enter Reg No to Auto-Load", placeholder="JLC/0001/26")
    student_class=None; student_name=""; subjects=[]
    if reg_no_input:
        df_stud = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_no_input}'", conn)
        if not df_stud.empty:
            student_class=df_stud.iloc[0]['class']; student_name=df_stud.iloc[0]['name']
            subjects=SUBJECTS_MAP.get(student_class, ["Mathematics","English","Kiswahili","Science","SST"])
            st.info(f"👨‍🎓 {student_name} | Class: {student_class} | Subjects: {', '.join(subjects)}")
        else:
            st.error("Reg not found")
    if subjects:
        with st.form("marks_form"):
            c1,c2=st.columns(2)
            term=c1.selectbox("Term",["Term 1","Term 2","Term 3"]); exam=c2.selectbox("Exam",["Opening","Mid Term","End Term"])
            marks={}; cols=st.columns(3)
            for i,subj in enumerate(subjects):
                marks[subj]=cols[i%3].number_input(subj,0,100,0, key=f"m_{subj}")
            if st.form_submit_button("Save Marks"):
                total=sum(marks.values()); mean=round(total/len(subjects),1) if subjects else 0
                grade="A" if mean>=80 else "B" if mean>=65 else "C" if mean>=50 else "D" if mean>=35 else "E"
                cur.execute("INSERT INTO academics (reg_no,term,exam_type,subjects_json,total,mean,grade,done_by) VALUES (?,?,?,?,?,?,?,?)", (reg_no_input, term, exam, json.dumps(marks), total, mean, grade, username)); conn.commit()
                log_action(username, role, "ACADEMICS", f"Saved marks for {reg_no_input} {student_class} Total {total} by {username}")
                st.success(f"Saved Total {total} Mean {mean} Grade {grade}")
    st.dataframe(pd.read_sql("SELECT reg_no,term,exam_type,total,mean,grade,done_by FROM academics ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Report Cards":
    st.subheader("Report Card Generator - CBC Presentable")

    def get_cbc_level(mark):
        if mark >= 76: return "EE"
        elif mark >= 51: return "ME"
        elif mark >= 26: return "AE"
        else: return "BE"

    def get_cbc_comment(level):
        if level=="EE": return "Exceeding Expectation - Excellent"
        if level=="ME": return "Meeting Expectation - Good"
        if level=="AE": return "Approaching Expectation - Fair"
        return "Below Expectation - Needs Support"

    def get_grade(mark):
        if mark>=80: return "A"
        if mark>=65: return "B"
        if mark>=50: return "C"
        if mark>=35: return "D"
        return "E"

    reg = st.text_input("Enter Reg No for Report Card (e.g JLC/0004/2024)", key="rep_reg")
    if reg:
        df_s = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg}'", conn)
        df_a = pd.read_sql(f"SELECT * FROM academics WHERE reg_no='{reg}' ORDER BY id DESC LIMIT 1", conn)
        if not df_s.empty and not df_a.empty:
            s=df_s.iloc[0]
            a=df_a.iloc[0]
            marks_dict = json.loads(a['subjects_json'])
            term = a['term']
            exam_type = a['exam_type']

            # Build HTML Report Card
            total = a['total']
            mean = a['mean']
            overall_level = get_cbc_level(mean)

            html_report = f"""
            <div style="border:3px solid #ff85a1; padding:20px; background:white; border-radius:15px; font-family: Arial;">
                <h1 style="text-align:center; color:#e91e63; margin:0;">JAWABU LEARNING CENTRE</h1>
                <p style="text-align:center; color:#ff4d7a; font-style:italic; margin:0;">Nurturing Competence • Building Character</p>
                <p style="text-align:center; font-size:12px;">P.O. Box 1234-00100, Nairobi | Tel: 0700 123 456</p>
                <hr style="border:1px solid #ff85a1;">

                <div style="background:#fff0f3; padding:10px; border-radius:10px; margin-bottom:15px;">
                    <table style="width:100%; border-collapse:collapse;">
                        <tr>
                            <td><b>Name:</b> {s['name']}</td>
                            <td><b>Class:</b> {s['class']}</td>
                            <td><b>Term:</b> {term}</td>
                        </tr>
                        <tr>
                            <td><b>Admission No:</b> {s['reg_no']}</td>
                            <td><b>Year:</b> {datetime.date.today().year}</td>
                            <td><b>Exam:</b> {exam_type}</td>
                        </tr>
                    </table>
                </div>

                <h3 style="text-align:center; background:#ffe4e9; padding:8px; border-radius:8px; color:#e91e63;">PERFORMANCE REPORT — COMPETENCY BASED CURRICULUM (CBC)</h3>

                <table style="width:100%; border-collapse:collapse; border:1px solid #ff85a1;">
                    <tr style="background:#ff85a1; color:white;">
                        <th style="padding:8px; border:1px solid #ff85a1; text-align:left;">Subject</th>
                        <th style="padding:8px; border:1px solid #ff85a1;">Marks (%)</th>
                        <th style="padding:8px; border:1px solid #ff85a1;">Grade</th>
                        <th style="padding:8px; border:1px solid #ff85a1;">CBC Level</th>
                        <th style="padding:8px; border:1px solid #ff85a1;">Comment</th>
                    </tr>
            """
            for subj, mark in marks_dict.items():
                level = get_cbc_level(mark)
                grade = get_grade(mark)
                comment = get_cbc_comment(level)
                html_report += f"""
                    <tr>
                        <td style="padding:6px; border:1px solid #ffc2d1;"><b>{subj}</b></td>
                        <td style="padding:6px; border:1px solid #ffc2d1; text-align:center;">{mark}</td>
                        <td style="padding:6px; border:1px solid #ffc2d1; text-align:center;">{grade}</td>
                        <td style="padding:6px; border:1px solid #ffc2d1; text-align:center; font-weight:bold;">{level}</td>
                        <td style="padding:6px; border:1px solid #ffc2d1; font-size:12px;">{comment}</td>
                    </tr>
                """

            html_report += f"""
                </table>
                <div style="display:flex; justify-content:space-between; background:#fff0f3; padding:10px; margin-top:15px; border-radius:10px;">
                    <div><b>TOTAL MARKS:</b><br><span style="font-size:18px; font-weight:bold;">{total} / {len(marks_dict)*100}</span></div>
                    <div><b>MEAN SCORE:</b><br><span style="font-size:18px; font-weight:bold;">{mean}%</span></div>
                    <div><b>OVERALL GRADE:</b><br><span style="font-size:18px; font-weight:bold;">{overall_level} - {get_cbc_comment(overall_level)}</span></div>
                </div>
                <div style="margin-top:15px; font-size:12px; background:#fff8f9; padding:10px; border-radius:8px;">
                    <b>CLASS TEACHER'S COMMENT:</b> {s['name']} is { 'diligent and hardworking, exceeds expectations' if mean>=76 else 'meeting expectations, good progress' if mean>=51 else 'approaching expectations, needs more effort'}. Keep it up!<br><br>
                    <b>Fee Balance:</b> Ksh {s['balance']} | <b>Generated by:</b> {username} on {datetime.date.today()}<br><br>
                    <b>EE</b> - Exceeding (76-100%) | <b>ME</b> - Meeting (51-75%) | <b>AE</b> - Approaching (26-50%) | <b>BE</b> - Below (0-25%)
                </div>
            </div>
            """

            st.markdown(html_report, unsafe_allow_html=True)

            # Download buttons
            c1,c2 = st.columns(2)
            # Text download
            txt_report = f"JAWABU LEARNING CENTRE\n{term} - {exam_type}\nName: {s['name']} Class: {s['class']} Reg: {reg}\n\n"
            for subj, mark in marks_dict.items():
                txt_report += f"{subj}: {mark}% - {get_cbc_level(mark)} - {get_cbc_comment(get_cbc_level(mark))}\n"
            txt_report += f"\nTotal: {total} Mean: {mean} Overall: {overall_level}\nFee Balance: {s['balance']}\n"
            c1.download_button("📄 Download as TXT", txt_report, file_name=f"{reg}_{exam_type}.txt")

            # Try PDF download
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0,10,"JAWABU LEARNING CENTRE",0,1,'C')
                pdf.set_font("Arial",'',10)
                pdf.cell(0,5,f"{term} - {exam_type}",0,1,'C')
                pdf.cell(0,5,f"Name: {s['name']} | Class: {s['class']} | Reg: {reg}",0,1,'C')
                pdf.ln(5)
                pdf.set_font("Arial",'B',10)
                pdf.cell(50,8,"Subject",1); pdf.cell(20,8,"Marks",1); pdf.cell(20,8,"Grade",1); pdf.cell(20,8,"Level",1); pdf.cell(80,8,"Comment",1); pdf.ln()
                pdf.set_font("Arial",'',9)
                for subj, mark in marks_dict.items():
                    pdf.cell(50,7,subj[:24],1); pdf.cell(20,7,str(mark),1); pdf.cell(20,7,get_grade(mark),1); pdf.cell(20,7,get_cbc_level(mark),1); pdf.cell(80,7,get_cbc_comment(get_cbc_level(mark))[:40],1); pdf.ln()
                pdf.ln(3)
                pdf.cell(0,8,f"Total: {total} Mean: {mean}% Overall: {overall_level} Balance: Ksh {s['balance']}",0,1)
                pdf_output = pdf.output(dest='S').encode('latin-1')
                c2.download_button("📕 Download PDF Report Card", pdf_output, file_name=f"{reg}_Report.pdf", mime="application/pdf")
            except Exception as e:
                c2.info("Add fpdf2 in requirements.txt to enable PDF")

            log_action(username, role, "REPORT CARD", f"Generated {exam_type} for {reg}")
        elif not df_s.empty:
            st.warning("No marks saved yet for this student. Go to Academics CBC first.")
        else:
            st.error("Student not found")

elif menu=="Fee Defaulters & Reports":
    st.subheader("Fee Defaulters")
    df=pd.read_sql("SELECT reg_no,name,class,parent_name,parent_phone,fee_total,paid,balance FROM students WHERE balance>0", conn)
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV", df.to_csv(index=False), "defaulters.csv")

elif menu=="User Management":
    if role!="DIRECTOR":
        st.error("Only Director can access"); st.stop()
    st.subheader("Director: Create / Disable Users")
    with st.form("create_user"):
        c1,c2,c3=st.columns(3)
        new_u=c1.text_input("New Username"); new_p=c2.text_input("Password"); new_r=c3.selectbox("Role",["ACCOUNTANT","TEACHER","DIRECTOR"])
        if st.form_submit_button("Create Account"):
            try:
                cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (new_u,new_p,new_r,1,username,str(datetime.datetime.now()))); conn.commit()
                log_action(username, role, "CREATE USER", f"Created {new_u} as {new_r}")
                st.success(f"Created {new_u}")
            except:
                st.error("Username already exists")
    st.divider()
    st.subheader("All Users")
    df_users = pd.read_sql("SELECT username,role,active,created_by,created_at FROM users", conn)
    st.dataframe(df_users, use_container_width=True)
    st.subheader("Disable / Enable Account")
    sel_user = st.selectbox("Select Username", df_users['username'].tolist())
    c1,c2=st.columns(2)
    if c1.button("🔴 DISABLE Account"):
        cur.execute("UPDATE users SET active=0 WHERE username=?", (sel_user,)); conn.commit()
        log_action(username, role, "DISABLE USER", f"Disabled {sel_user}")
        st.warning(f"{sel_user} disabled")
    if c2.button("🟢 ENABLE Account"):
        cur.execute("UPDATE users SET active=1 WHERE username=?", (sel_user,)); conn.commit()
        log_action(username, role, "ENABLE USER", f"Enabled {sel_user}")
        st.success(f"{sel_user} enabled")

elif menu=="Audit Logs":
    if role!="DIRECTOR":
        st.error("Only Director"); st.stop()
    st.subheader("Audit Trail - Who Did What")
    df_log = pd.read_sql("SELECT timestamp,username,role,action,details FROM audit_logs ORDER BY id DESC", conn)
    st.dataframe(df_log, use_container_width=True)
    st.download_button("Download Audit CSV", df_log.to_csv(index=False), "audit_logs.csv")
