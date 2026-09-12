import streamlit as st
import pandas as pd
import datetime, os, json, sqlite3

st.set_page_config(page_title="JAWABU LEARNING CENTRE", page_icon="🏫", layout="wide")
st.markdown("""
<style>
.stApp {background: #fff0f3;}
h1,h2,h3 {color: #ff4d7a!important;}
div[data-testid="stMetric"] {background:white; border:1px solid #ffe4e9; border-radius:20px; padding:10px;}
.stButton>button {background:#ff85a1; color:white; border-radius:12px; border:none; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

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

cur.execute("CREATE TABLE IF NOT EXISTS students (reg_no TEXT PRIMARY KEY, name TEXT, parent_name TEXT, parent_phone TEXT, class TEXT, gender TEXT, dob TEXT, nemis TEXT, adm_date TEXT, fee_total INT, paid INT, balance INT, arrears INT)")
cur.execute("CREATE TABLE IF NOT EXISTS mpesa_trans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, reg_no TEXT, mpesa_code TEXT, amount INT, phone TEXT, tuition INT, transport INT, library INT, status TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, type TEXT, amount INT, description TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS academics (id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT, term TEXT, exam_type TEXT, subjects_json TEXT, total INT, mean REAL, grade TEXT, done_by TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, active INT, created_by TEXT, created_at TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, username TEXT, role TEXT, action TEXT, details TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS school_settings (id INT PRIMARY KEY, paybill TEXT, till TEXT, account_name TEXT)")

if pd.read_sql("SELECT * FROM users", conn).empty:
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("admin","Jawabu@2026","DIRECTOR",1,"system",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("accountant","Acc@2026","ACCOUNTANT",1,"admin",str(datetime.datetime.now())))
    cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("teacher","Teach@2026","TEACHER",1,"admin",str(datetime.datetime.now())))
    conn.commit()
if pd.read_sql("SELECT * FROM school_settings", conn).empty:
    cur.execute("INSERT INTO school_settings VALUES (1,'247247','4123456','JAWABU LEARNING CENTRE')")
    conn.commit()

def log_action(username, role, action, details):
    cur.execute("INSERT INTO audit_logs (timestamp,username,role,action,details) VALUES (?,?,?,?,?)", (str(datetime.datetime.now()), username, role, action, details))
    conn.commit()

settings = pd.read_sql("SELECT * FROM school_settings WHERE id=1", conn).iloc[0]
PAYBILL = settings['paybill']
TILL = settings['till']

if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center'>JAWABU LEARNING CENTRE</h1>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#ffe4e9; border:2px dashed #ff85a1; padding:15px; border-radius:15px; text-align:center; margin-bottom:15px;">
        <h2 style="margin:0; color:#e91e63;">LIPA NA M-PESA</h2>
        <p style="font-size:24px; font-weight:bold; margin:5px;">Paybill: {PAYBILL} | Till: {TILL}</p>
        <p style="margin:0;"><b>Account No:</b> Student Reg No e.g JLC/0001/26</p>
    </div>
    """, unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            u=st.text_input("Username")
            p=st.text_input("Password", type="password")
            if st.button("LOGIN", use_container_width=True):
                df_user = pd.read_sql(f"SELECT * FROM users WHERE username='{u}' AND password='{p}'", conn)
                if not df_user.empty and df_user.iloc[0]['active']==1:
                    st.session_state.logged_in=True; st.session_state.username=u; st.session_state.role=df_user.iloc[0]['role']
                    log_action(u, df_user.iloc[0]['role'], "LOGIN", "Logged in"); st.rerun()
                elif not df_user.empty and df_user.iloc[0]['active']==0:
                    st.error("Account DISABLED by Director")
                else:
                    st.error("Wrong credentials")
    st.stop()

username = st.session_state.username
role = st.session_state.role
st.sidebar.markdown(f"### JAWABU\n**User:** {username}\n**Role:** {role}")

if role=="ACCOUNTANT":
    menu_options = ["Admissions","Finance - Auto STK","Expenses","Fee Defaulters & Reports"]
elif role=="TEACHER":
    menu_options = ["Academics CBC","Report Cards"]
else:
    menu_options = ["Director Dashboard","Admissions","Finance - Auto STK","Expenses","Academics CBC","Report Cards","Fee Defaulters & Reports","School Settings","User Management","Audit Logs"]

menu = st.sidebar.radio("MENU", menu_options)
if st.sidebar.button("Logout"):
    log_action(username, role, "LOGOUT", "Logged out"); st.session_state.logged_in=False; st.rerun()

if menu=="Director Dashboard":
    df_exp = pd.read_sql("SELECT * FROM expenses", conn); df_mp = pd.read_sql("SELECT * FROM mpesa_trans", conn)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Collected", f"Ksh {df_mp['amount'].sum() if not df_mp.empty else 0}")
    c2.metric("Expenses", f"Ksh {df_exp['amount'].sum() if not df_exp.empty else 0}")
    c3.metric("PROFIT", f"Ksh {(df_mp['amount'].sum() if not df_mp.empty else 0)-(df_exp['amount'].sum() if not df_exp.empty else 0)}")
    c4.metric("Students", pd.read_sql("SELECT * FROM students", conn).shape[0])
    st.write(f"Current Paybill: {PAYBILL} | Till: {TILL}")
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
            log_action(username, role, "ADMISSION", f"Admitted {reg} {s_name}"); st.success(f"Admitted {reg}")
    st.dataframe(pd.read_sql("SELECT reg_no,name,class,parent_phone,balance FROM students", conn), use_container_width=True)

elif menu=="Finance - Auto STK":
    st.subheader("Finance - Auto Reflect Class")
    st.info(f"Parents Pay via Paybill {PAYBILL} Account = Reg No | Till {TILL}")
    reg_input = st.text_input("Enter Reg No")
    student = None
    if reg_input:
        df = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_input}'", conn)
        if not df.empty:
            s=df.iloc[0]; student=s; st.success(f"Found: {s['name']} | Class: {s['class']} | Balance: Ksh {s['balance']}")
        else:
            st.error("Reg No not found")
    phone_auto = student['parent_phone'] if student is not None else ""
    with st.form("pay"):
        c1,c2=st.columns(2)
        amount=c1.number_input("Amount", min_value=1); phone=c2.text_input("Phone", value=phone_auto)
        if st.form_submit_button("SEND STK & RECORD"):
            if student is None:
                st.error("Enter valid Reg No first")
            else:
                tuition=int(amount*0.8); transport=int(amount*0.15); library=amount-tuition-transport
                code=f"QAH{os.urandom(2).hex().upper()}"
                cur.execute("INSERT INTO mpesa_trans (date,reg_no,mpesa_code,amount,phone,tuition,transport,library,status,done_by) VALUES (?,?,?,?,?,?,?,?,?,?)", (str(datetime.datetime.now()), reg_input, code, int(amount), phone, tuition, transport, library, "VERIFIED", username))
                cur.execute("UPDATE students SET paid=paid+?, balance=balance-? WHERE reg_no=?", (int(amount), int(amount), reg_input)); conn.commit()
                log_action(username, role, "FINANCE", f"{reg_input} paid {amount}"); st.success(f"Recorded {code}")
    st.dataframe(pd.read_sql("SELECT date,reg_no,mpesa_code,amount,done_by,status FROM mpesa_trans ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Expenses":
    st.subheader("Expenses")
    with st.form("exp"):
        c1,c2,c3=st.columns(3)
        t=c1.selectbox("Type",["Salary","Food","Books","Electricity","Wifi"]); a=c2.number_input("Amount"); d=c3.text_input("Desc")
        if st.form_submit_button("Add Expense"):
            cur.execute("INSERT INTO expenses (date,type,amount,description,done_by) VALUES (?,?,?,?,?)", (str(datetime.date.today()),t,a,d,username)); conn.commit()
            log_action(username, role, "EXPENSE", f"{t} {a}"); st.success("Added")
    st.dataframe(pd.read_sql("SELECT * FROM expenses ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Academics CBC":
    st.subheader("CBC - Auto Subjects by Class")
    reg_no_input = st.text_input("Enter Reg No to Auto-Load", placeholder="JLC/0001/26")
    student_class=None; subjects=[]
    if reg_no_input:
        df_stud = pd.read_sql(f"SELECT * FROM students WHERE reg_no='{reg_no_input}'", conn)
        if not df_stud.empty:
            student_class=df_stud.iloc[0]['class']; student_name=df_stud.iloc[0]['name']
            subjects=SUBJECTS_MAP.get(student_class, [])
            st.info(f"Student: {student_name} | Class: {student_class} | Subjects: {', '.join(subjects)}")
    if subjects:
        with st.form("marks_form"):
            c1,c2=st.columns(2)
            term=c1.selectbox("Term",["Term 1","Term 2","Term 3"]); exam=c2.selectbox("Exam",["Opening","Mid Term","End Term"])
            marks={}; cols=st.columns(3)
            for i,subj in enumerate(subjects):
                marks[subj]=cols[i%3].number_input(subj,0,100,0, key=f"m_{subj}")
            if st.form_submit_button("Save Marks"):
                total=sum(marks.values()); mean=round(total/len(subjects),1)
                grade="A" if mean>=80 else "B" if mean>=65 else "C" if mean>=50 else "D" if mean>=35 else "E"
                cur.execute("INSERT INTO academics (reg_no,term,exam_type,subjects_json,total,mean,grade,done_by) VALUES (?,?,?,?,?,?,?,?)", (reg_no_input, term, exam, json.dumps(marks), total, mean, grade, username)); conn.commit()
                log_action(username, role, "ACADEMICS", f"Saved {reg_no_input} {total}"); st.success(f"Saved Total {total} Mean {mean} Grade {grade}")
    st.dataframe(pd.read_sql("SELECT reg_no,term,exam_type,total,mean,grade,done_by FROM academics ORDER BY id DESC", conn), use_container_width=True)

elif menu=="Report Cards":
    from fpdf import FPDF
import datetime

# ---- Report Card - CBC Presentable ----
st.subheader("Report Card - CBC Presentable")

reg_no = st.text_input("Enter Reg No for Report Card")

if reg_no:
    # fetch student
    c.execute("SELECT * FROM students WHERE reg_no=?", (reg_no,))
    student = c.fetchone()

    if not student:
        st.error("Student not found!")
    else:
        # fetch marks
        c.execute("SELECT subject, score, grade FROM academics WHERE reg_no=?", (reg_no,))
        marks = c.fetchall()

        if not marks:
            st.warning("No marks found for this student")
        else:
            # Show report on screen
            st.markdown(f"### {student[1]} - {student[2]} - {student[3]}")
            df_marks = pd.DataFrame(marks, columns=["Subject","Score","Grade"])
            st.table(df_marks)

            # --- CREATE PDF FOR DOWNLOAD ---
            def create_report_pdf():
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "JAWABU LEARNING CENTRE - CBC REPORT CARD", ln=True, align="C")
                pdf.ln(10)
                pdf.set_font("Arial", "", 12)
                pdf.cell(0, 8, f"Name: {student[1]} | Reg No: {student[2]} | Class: {student[3]}", ln=True)
                pdf.cell(0, 8, f"Date: {datetime.date.today()}", ln=True)
                pdf.ln(10)

                # table header
                pdf.set_font("Arial", "B", 12)
                pdf.cell(60, 10, "Subject", border=1)
                pdf.cell(40, 10, "Score", border=1)
                pdf.cell(40, 10, "Grade", border=1, ln=True)

                pdf.set_font("Arial", "", 12)
                for subj, score, grade in marks:
                    pdf.cell(60, 10, str(subj), border=1)
                    pdf.cell(40, 10, str(score), border=1)
                    pdf.cell(40, 10, str(grade), border=1, ln=True)

                pdf.ln(10)
                pdf.cell(0, 10, "Class Teacher Signature: ________________", ln=True)
                return pdf.output(dest="S").encode("latin1")

            pdf_bytes = create_report_pdf()

            # DOWNLOAD BUTTON - This is what you want
            st.download_button(
                label="📥 Download Report Card PDF",
                data=pdf_bytes,
                file_name=f"ReportCard_{reg_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

elif menu=="Fee Defaulters & Reports":
    df=pd.read_sql("SELECT reg_no,name,class,parent_name,parent_phone,fee_total,paid,balance FROM students WHERE balance>0", conn)
    st.dataframe(df, use_container_width=True); st.download_button("Download CSV", df.to_csv(index=False), "defaulters.csv")

elif menu=="School Settings":
    if role!="DIRECTOR":
        st.error("Only Director"); st.stop()
    st.subheader("School M-Pesa Settings")
    curr = pd.read_sql("SELECT * FROM school_settings WHERE id=1", conn).iloc[0]
    with st.form("settings_form"):
        c1,c2=st.columns(2)
        new_paybill=c1.text_input("Paybill Number", value=curr['paybill'])
        new_till=c2.text_input("Till Number", value=curr['till'])
        new_name=st.text_input("School Name", value=curr['account_name'])
        if st.form_submit_button("Save Paybill"):
            cur.execute("UPDATE school_settings SET paybill=?, till=?, account_name=? WHERE id=1", (new_paybill, new_till, new_name)); conn.commit()
            log_action(username, role, "SETTINGS", f"Changed Paybill to {new_paybill}"); st.success(f"Saved! New Paybill: {new_paybill}"); st.rerun()
    st.markdown(f"### Parents pay: Paybill {curr['paybill']} Account = Reg No | Till {curr['till']}")

elif menu=="User Management":
    if role!="DIRECTOR":
        st.error("Only Director"); st.stop()
    st.subheader("Create / Disable Users")
    with st.form("create_user"):
        c1,c2,c3=st.columns(3)
        new_u=c1.text_input("New Username"); new_p=c2.text_input("Password"); new_r=c3.selectbox("Role",["ACCOUNTANT","TEACHER","DIRECTOR"])
        if st.form_submit_button("Create Account"):
            try:
                cur.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (new_u,new_p,new_r,1,username,str(datetime.datetime.now()))); conn.commit()
                log_action(username, role, "CREATE USER", f"Created {new_u}"); st.success(f"Created {new_u}")
            except:
                st.error("Username exists")
    df_users = pd.read_sql("SELECT username,role,active,created_by FROM users", conn)
    st.dataframe(df_users, use_container_width=True)
    sel_user = st.selectbox("Select Username", df_users['username'].tolist())
    c1,c2=st.columns(2)
    if c1.button("DISABLE"):
        cur.execute("UPDATE users SET active=0 WHERE username=?", (sel_user,)); conn.commit(); log_action(username, role, "DISABLE USER", f"Disabled {sel_user}"); st.warning(f"{sel_user} disabled")
    if c2.button("ENABLE"):
        cur.execute("UPDATE users SET active=1 WHERE username=?", (sel_user,)); conn.commit(); log_action(username, role, "ENABLE USER", f"Enabled {sel_user}"); st.success(f"{sel_user} enabled")

elif menu=="Audit Logs":
    if role!="DIRECTOR":
        st.error("Only Director"); st.stop()
    st.subheader("Who Did What")
    df_log = pd.read_sql("SELECT timestamp,username,role,action,details FROM audit_logs ORDER BY id DESC", conn)
    st.dataframe(df_log, use_container_width=True)
    st.download_button("Download Audit CSV", df_log.to_csv(index=False), "audit_logs.csv")
