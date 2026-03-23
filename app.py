import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime, timedelta
import json

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="Alomari Creator OS", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# CSS - تصميم آمن، واجهة امتحانات محسنة، وتنسيق نظيف
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    html, body, p, h1, h2, h3, h4, h5, h6, label, input, textarea, select, button { 
        font-family: 'Tajawal', sans-serif; 
    }
    
    .stApp { background-color: #f4f7fb; }
    h1, h2, h3, h4, h5, h6 { font-weight: 700; color: #1e293b; }
    
    .animate-fade { animation: fadeIn 0.4s ease-out forwards; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    /* توحيد أحجام التبويبات في الشريط الجانبي */
    div[role="radiogroup"] { gap: 10px !important; padding-top: 10px;}
    div[role="radiogroup"] > label {
        width: 100%; 
        display: block; 
        background-color: #ffffff; 
        border: 1px solid #e2e8f0; 
        padding: 12px 15px; 
        border-radius: 10px; 
        cursor: pointer; 
        margin: 0; 
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        box-sizing: border-box;
    }
    div[role="radiogroup"] > label:hover { 
        background-color: #f8fafc; 
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-color: #cbd5e1;
    }
    div[role="radiogroup"] > label[aria-checked="true"] { 
        background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%) !important; 
        border-right: 5px solid #2563eb;
        border-left: 1px solid #bfdbfe;
        border-top: 1px solid #bfdbfe;
        border-bottom: 1px solid #bfdbfe;
        box-shadow: 0 4px 10px rgba(37,99,235,0.1);
    }
    div[role="radiogroup"] > label > div:first-child { display: none !important; } 
    div[role="radiogroup"] > label p { font-size: 1.05rem; font-weight: 600; margin: 0; color: #475569; }
    div[role="radiogroup"] > label[aria-checked="true"] p { color: #1e3a8a; font-weight: 800; }

    .profile-box {
        text-align: center; padding: 25px 15px; margin-bottom: 15px; 
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); 
        border-radius: 16px; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.15);
    }
    .profile-box h3 { color: white !important; font-size: 1.3rem !important; margin:0;}
    .profile-box h4 { color: #cbd5e1 !important; font-size: 1rem !important; margin-top:5px;}
    
    [data-testid="stExpander"] {
        background-color: #ffffff; border-radius: 10px !important; border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 12px;
    }
    
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] {
        padding: 8px !important;
        border-radius: 12px;
    }
    
    /* 📱 تحسينات الموبايل */
    @media (max-width: 768px) {
        .profile-box { padding: 15px 10px; }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# دالة تحويل الوقت 
# ==========================================
def format_to_12hr(time_str):
    if pd.isna(time_str) or str(time_str).strip() == "": return "غير محدد"
    try:
        t = pd.to_datetime(str(time_str)).strftime("%I:%M %p")
        return t.replace("AM", "ص").replace("PM", "م")
    except:
        return str(time_str)

# ==========================================
# 2. الربط مع جوجل شيت 
# ==========================================
@st.cache_resource(ttl=60)
def get_google_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        else:
            creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    except Exception as e:
        st.error(f"⚠️ مشكلة في بيانات الربط: {e}")
        st.stop()

    client = gspread.authorize(creds)
    spreadsheet = client.open("Dashboard")
    
    tracker_sheet = spreadsheet.worksheet("Lectures Tracker")
    records_l = tracker_sheet.get_all_records()
    df_l = pd.DataFrame(records_l) if records_l else pd.DataFrame()
    if not df_l.empty:
        if 'Exam' not in df_l.columns: df_l['Exam'] = 'Unassigned'
        if 'Note' not in df_l.columns: df_l['Note'] = ''
        
    cal_cols = ["Date", "Time", "Subject", "Note", "Status"]
    try:
        cal_sheet = spreadsheet.worksheet("Calendar")
        c_recs = cal_sheet.get_all_records()
        if not c_recs:
            df_c = pd.DataFrame(columns=cal_cols)
            if len(cal_sheet.get_all_values()) == 0: cal_sheet.update(range_name='A1', values=[cal_cols])
        else:
            df_c = pd.DataFrame(c_recs)
            for col in cal_cols:
                if col not in df_c.columns: df_c[col] = "Pending" if col == "Status" else ""
    except: cal_sheet, df_c = None, pd.DataFrame(columns=cal_cols)
        
    tasks_cols = ["Subject", "Task Type", "Task Name", "Status", "Note"]
    try:
        tasks_sheet = spreadsheet.worksheet("Tasks")
        t_recs = tasks_sheet.get_all_records()
        if not t_recs:
            df_t = pd.DataFrame(columns=tasks_cols)
            if len(tasks_sheet.get_all_values()) == 0: tasks_sheet.update(range_name='A1', values=[tasks_cols])
        else:
            df_t = pd.DataFrame(t_recs)
            for col in tasks_cols:
                if col not in df_t.columns: df_t[col] = ""
    except: tasks_sheet, df_t = None, pd.DataFrame(columns=tasks_cols)
        
    exams_cols = ["Subject", "Exam", "Date"]
    try:
        exams_sheet = spreadsheet.worksheet("Exam Dates")
    except:
        try:
            exams_sheet = spreadsheet.add_worksheet(title="Exam Dates", rows="100", cols="3")
            exams_sheet.update(range_name='A1', values=[exams_cols])
        except: exams_sheet = None
        
    if exams_sheet is not None:
        try:
            e_recs = exams_sheet.get_all_records()
            if not e_recs:
                df_e = pd.DataFrame(columns=exams_cols)
                if len(exams_sheet.get_all_values()) == 0: exams_sheet.update(range_name='A1', values=[exams_cols])
            else:
                df_e = pd.DataFrame(e_recs)
                for col in exams_cols:
                    if col not in df_e.columns: df_e[col] = ""
        except: df_e = pd.DataFrame(columns=exams_cols)
    else: df_e = pd.DataFrame(columns=exams_cols)

    todo_cols = ["Task Name", "Status", "Date"]
    try:
        todo_sheet = spreadsheet.worksheet("Daily ToDo")
    except:
        try:
            todo_sheet = spreadsheet.add_worksheet(title="Daily ToDo", rows="100", cols="3")
            todo_sheet.update(range_name='A1', values=[todo_cols])
        except: todo_sheet = None
        
    if todo_sheet is not None:
        try:
            td_recs = todo_sheet.get_all_records()
            if not td_recs:
                df_todo = pd.DataFrame(columns=todo_cols)
                if len(todo_sheet.get_all_values()) == 0: todo_sheet.update(range_name='A1', values=[todo_cols])
            else:
                df_todo = pd.DataFrame(td_recs)
                for col in todo_cols:
                    if col not in df_todo.columns: df_todo[col] = ""
        except: df_todo = pd.DataFrame(columns=todo_cols)
    else: df_todo = pd.DataFrame(columns=todo_cols)

    return df_l, df_c, df_t, df_e, df_todo, tracker_sheet, cal_sheet, tasks_sheet, exams_sheet, todo_sheet

df_lectures, df_calendar, df_tasks, df_exams, df_todo, tracker_sheet, cal_sheet, tasks_sheet, exams_sheet, todo_sheet = get_google_data()

# ==========================================
# 3. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    current_hour = datetime.now().hour
    greeting = "صباح الخير ☀️" if current_hour < 12 else "مساء الخير 🌙"
    
    st.markdown(f"<div class='profile-box'><h3 style='margin:0;'>{greeting}</h3><h4>د. محمد العمري</h4></div>", unsafe_allow_html=True)
    
    if not df_lectures.empty:
        total_global = len(df_lectures)
        done_global = len(df_lectures[df_lectures['Status'].isin(['Done', 'Uploaded'])])
        prog_global = int((done_global / total_global) * 100) if total_global > 0 else 0
        
        st.markdown(f"""
        <div style='padding:15px; background:#ffffff; border: 1px solid #e2e8f0; border-radius:12px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);'>
            <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                <b style='color:#1e293b; font-size:0.95rem;'>الإنجاز الكلي</b>
                <b style='color:#10b981;'>{prog_global}%</b>
            </div>
            <div style='width:100%; background:#e2e8f0; height:8px; border-radius:4px;'>
                <div style='width:{prog_global}%; background:#10b981; height:100%; border-radius:4px; transition: width 0.5s ease-in-out;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='color:#64748b; font-weight:700; margin-bottom:5px; font-size:1rem;'>📂 مساحات العمل والتبويبات</div>", unsafe_allow_html=True)
    if not df_lectures.empty:
        subjects = ["🏠 الصفحة الرئيسية"] + list(df_lectures['Subject'].unique())
        selected_subject = st.radio("القائمة:", subjects, label_visibility="collapsed")

# إعدادات الألوان للامتحانات
status_map = {
    'Done': {'icon': '✅', 'color': '#10b981', 'bg': '#ecfdf5', 'label': 'منجزة'},
    'In Progress': {'icon': '⏳', 'color': '#f59e0b', 'bg': '#fffbeb', 'label': 'قيد العمل'},
    'To Edit': {'icon': '🛠️', 'color': '#ef4444', 'bg': '#fef2f2', 'label': 'تعديل'},
    'Not Started': {'icon': '🔴', 'color': '#64748b', 'bg': '#f8fafc', 'label': 'لم تبدأ'}
}
exam_colors = {
    "First": ("#f0fdf4", "#86efac", "#166534"), 
    "Second": ("#fdf4ff", "#d8b4fe", "#701a75"),
    "Mid": ("#fffbeb", "#fde68a", "#92400e"), 
    "Final": ("#eff6ff", "#bfdbfe", "#1e3a8a"), 
    "Unassigned": ("#f8fafc", "#e2e8f0", "#334155")
}
default_exam_color = ("#f8fafc", "#cbd5e1", "#334155") 

# ==========================================
# 4. التوجيه (Routing)
# ==========================================

if selected_subject == "🏠 الصفحة الرئيسية":
    st.markdown("<h2>🏠 لوحة القيادة (Overview)</h2>", unsafe_allow_html=True)
    
    if not df_exams.empty:
        upcoming_exams = []
        for _, r in df_exams.iterrows():
            try:
                e_date = datetime.strptime(str(r['Date']).strip(), "%Y-%m-%d").date()
                diff = (e_date - datetime.now().date()).days
                if diff >= 0:  
                    upcoming_exams.append({
                        'Subject': r['Subject'], 
                        'Exam': r['Exam'], 
                        'Days': diff, 
                        'DateStr': str(r['Date']).strip()
                    })
            except: pass
                
        if upcoming_exams:
            st.markdown("<h3 style='color:#1e293b; margin-top:20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;'>⏳ الامتحانات القادمة</h3>", unsafe_allow_html=True)
            upcoming_exams = sorted(upcoming_exams, key=lambda x: x['Days'])
            cols_ex = st.columns(min(len(upcoming_exams), 4)) 
            
            for i, ex in enumerate(upcoming_exams[:4]):
                with cols_ex[i]:
                    if ex['Days'] == 0:
                        color_bg, color_text, days_text = "#fef2f2", "#ef4444", "اليوم!"
                    elif ex['Days'] <= 3:
                        color_bg, color_text, days_text = "#fef2f2", "#ef4444", f"باقي {ex['Days']} أيام"
                    elif ex['Days'] <= 7:
                        color_bg, color_text, days_text = "#fffbeb", "#d97706", f"باقي {ex['Days']} يوم"
                    else:
                        color_bg, color_text, days_text = "#f0fdf4", "#10b981", f"باقي {ex['Days']} يوم"
                        
                    st.markdown(f"""
                    <div style='background:{color_bg}; border:1px solid {color_text}40; padding:15px; border-radius:10px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;'>
                        <div style='font-weight:bold; color:#1e293b; font-size:1.1rem;'>{ex['Subject']}</div>
                        <div style='font-size:0.9rem; color:#64748b; font-weight:600;'>{ex['Exam']}</div>
                        <div style='font-weight:800; font-size:1.3rem; color:{color_text}; margin-top:5px;'>{days_text}</div>
                        <div style='font-size:0.8rem; color:#94a3b8; margin-top:2px;'>📅 {ex['DateStr']}</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    if not df_calendar.empty:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow_events = df_calendar[(df_calendar['Date'] == tomorrow) & (df_calendar['Status'] != 'Done')]
        if not tomorrow_events.empty:
            for _, ev in tomorrow_events.iterrows():
                st.warning(f"🚨 **تذكير وجاهي غداً!** لديك موعد: {ev.get('Subject')} الساعة {format_to_12hr(ev.get('Time'))}", icon="📅")
    
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.markdown("<h3 style='color:#1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;'>🗓️ الجدول والمواعيد</h3>", unsafe_allow_html=True)
        
        with st.container(height=500, border=False):
            if cal_sheet is not None:
                with st.expander("⚙️ إضافة أو إدارة المواعيد"):
                    with st.form("add_cal_form_home", clear_on_submit=True):
                        c_date = st.date_input("التاريخ")
                        c_time = st.time_input("الوقت")
                        c_sub = st.text_input("العنوان (مثال: وجاهي أناتومي)")
                        c_note = st.text_area("ملاحظات (اختياري)")
                        if st.form_submit_button("حفظ الموعد", use_container_width=True):
                            cal_sheet.append_row([str(c_date), str(c_time), c_sub, c_note, 'Pending'])
                            get_google_data.clear()
                            st.rerun()
                    
                    st.markdown("---")
                    st.markdown("**✏️ تعديل أو حذف المواعيد الحالية:**")
                    if not df_calendar.empty:
                        for idx, row in df_calendar.iterrows():
                            if str(row.get('Status', '')) == 'Done': continue
                            sub_text = str(row.get('Subject', 'بدون عنوان'))
                            with st.popover(f"📅 {row.get('Date', '')} | {sub_text}", use_container_width=True):
                                with st.form(f"edit_cal_{idx}"):
                                    e_date = st.text_input("التاريخ", value=str(row.get('Date', '')))
                                    e_time = st.text_input("الوقت", value=str(row.get('Time', '')))
                                    e_sub = st.text_input("العنوان", value=sub_text)
                                    e_note = st.text_area("ملاحظات", value=str(row.get('Note', '')))
                                    
                                    c_save, c_del = st.columns(2)
                                    if c_save.form_submit_button("💾 حفظ", use_container_width=True):
                                        cal_sheet.update(range_name=f'A{idx+2}:D{idx+2}', values=[[e_date, e_time, e_sub, e_note]])
                                        get_google_data.clear()
                                        st.rerun()
                                    if c_del.form_submit_button("🗑️ حذف", use_container_width=True):
                                        cal_sheet.delete_rows(idx + 2)
                                        get_google_data.clear()
                                        st.rerun()

            if not df_calendar.empty:
                pending_cal = df_calendar[df_calendar['Status'] != 'Done']
                if not pending_cal.empty:
                    for idx, row in pending_cal.sort_values('Date').iterrows():
                        subj_val = str(row.get('Subject', '')).strip() or "📌 موعد بدون عنوان"
                        date_val = str(row.get('Date', '')).strip()
                        time_val = format_to_12hr(row.get('Time', ''))
                        note_val = str(row.get('Note', '')).strip()
                        
                        with st.container(border=True):
                            cc_btn, cc_text = st.columns([1.5, 4], vertical_alignment="center")
                            with cc_btn:
                                if st.button("✅ إنجاز", key=f"done_cal_{idx}", use_container_width=True):
                                    cal_sheet.update_cell(idx + 2, 5, 'Done') 
                                    get_google_data.clear()
                                    st.rerun()
                            with cc_text:
                                st.markdown(f"<div style='text-align:right; color: #1e3a8a; font-weight: 800; font-size: 1.1rem; margin-bottom: 5px;'>{subj_val}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align:right;'><span style='background: #eff6ff; color: #2563eb; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-left: 5px;'>📅 {date_val}</span><span style='background: #fef2f2; color: #ef4444; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold;'>⏰ {time_val}</span></div>", unsafe_allow_html=True)
                                if note_val: st.markdown(f"<div style='text-align:right; color: #64748b; font-size: 0.85rem; margin-top: 5px;'>📝 {note_val}</div>", unsafe_allow_html=True)
                else:
                    st.success("تم إنجاز جميع المواعيد القادمة! 🎉")
            else:
                st.info("لا توجد مواعيد وجاهية قادمة.")

    with col2:
        st.markdown("<h3 style='color:#1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;'>🎯 خطة اليوم (Daily To-Do)</h3>", unsafe_allow_html=True)
        
        with st.form("todo_add_form", clear_on_submit=True):
            st.markdown("<div style='font-size:0.9rem; font-weight:bold; color:#475569; margin-bottom:5px;'>ماذا ستنجز اليوم؟</div>", unsafe_allow_html=True)
            
            existing_tasks_list = ["-- اكتب مهمة جديدة أو اختر من المتراكم --"]
            if not df_tasks.empty:
                pending_t = df_tasks[df_tasks['Status'] != 'Done']
                for _, r in pending_t.iterrows():
                    existing_tasks_list.append(f"{r['Task Name']} ({r['Subject']} - {r['Task Type']})")
            
            selected_existing = st.selectbox("اختر من المهام المتراكمة:", existing_tasks_list, label_visibility="collapsed")
            custom_task = st.text_input("أو اكتب مهمة جديدة حرة:", placeholder="مثال: طباعة الشيتات...", label_visibility="collapsed")
            
            if st.form_submit_button("إضافة للقائمة ➕", use_container_width=True):
                task_to_add = custom_task.strip() if custom_task.strip() else (selected_existing if selected_existing != "-- اكتب مهمة جديدة أو اختر من المتراكم --" else "")
                if task_to_add:
                    if todo_sheet is not None:
                        todo_sheet.append_row([task_to_add, "Pending", str(datetime.now().date())])
                        get_google_data.clear()
                        st.rerun()
        
        with st.container(height=350, border=False):
            if not df_todo.empty:
                pending_todo = df_todo[df_todo['Status'] != 'Done']
                if not pending_todo.empty:
                    for idx, row in pending_todo.iterrows():
                        with st.container(border=True):
                            tc_btn, tc_text, tc_del = st.columns([2.5, 6, 1.5], vertical_alignment="center")
                            with tc_btn:
                                # 🌟 التعديل: إرجاع زر الإنجاز الأصلي الواضح
                                if st.button("✅ إنجاز", key=f"td_done_{idx}", help="تم الإنجاز", use_container_width=True):
                                    todo_sheet.update_cell(idx + 2, 2, 'Done')
                                    if not df_tasks.empty:
                                        for t_idx, t_row in df_tasks.iterrows():
                                            if f"{t_row['Task Name']} ({t_row['Subject']} - {t_row['Task Type']})" == row['Task Name']:
                                                tasks_sheet.update_cell(t_idx + 2, 4, 'Done')
                                                break
                                    get_google_data.clear()
                                    st.rerun()
                            with tc_text:
                                st.markdown(f"<div style='font-size:1rem; font-weight:700; color:#1e293b; text-align:right;'>{row['Task Name']}</div>", unsafe_allow_html=True)
                            with tc_del:
                                if st.button("🗑️", key=f"td_del_{idx}", help="حذف", use_container_width=True):
                                    todo_sheet.delete_rows(idx + 2)
                                    get_google_data.clear()
                                    st.rerun()
                else:
                    st.success("لقد أنهيت جميع مهام اليوم! يوم مثمر بامتياز ☕")
            else:
                st.info("اكتب مهامك لليوم في الصندوق أعلاه 👆")

    st.markdown("<hr style='border: 1px dashed #cbd5e1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#1e293b; margin-bottom: 20px;'>📊 نسبة الإنجاز في المواد (محاضرات ومهام)</h3>", unsafe_allow_html=True)
    
    # 🌟 التعديل الجذري لمنع تسرب الـ HTML وتنسيق الشبكة 🌟
    if not df_lectures.empty:
        all_subjects = [s for s in df_lectures['Subject'].unique() if str(s).strip() != ""]
        cols_prog = st.columns(3) 
        for i, subj in enumerate(all_subjects):
            subj_df = df_lectures[df_lectures['Subject'] == subj]
            total = len(subj_df)
            done = len(subj_df[subj_df['Status'].isin(['Done', 'Uploaded'])])
            pct = int((done / total) * 100) if total > 0 else 0
            
            with cols_prog[i % 3]:
                with st.expander(f"📚 {subj} | المنجز: {pct}%"):
                    st.markdown(f"""
                    <div style='width: 100%; background-color: #e2e8f0; border-radius: 8px; height: 8px; margin-bottom:15px; overflow:hidden;'>
                        <div style='width: {pct}%; background-color: #10b981; height: 100%; border-radius: 8px;'></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    subj_exams = [e for e in subj_df['Exam'].unique() if str(e).strip() != ""]
                    if subj_exams:
                        # كتابة الكود بسطر واحد لمنع الـ Markdown من اعتباره كود بلوك
                        exam_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;'>"
                        for ex in subj_exams:
                            ex_df = subj_df[subj_df['Exam'] == ex]
                            if not ex_df.empty:
                                ex_total = len(ex_df)
                                ex_done = len(ex_df[ex_df['Status'].isin(['Done', 'Uploaded'])])
                                c_color = "#10b981" if ex_done == ex_total else "#f59e0b" if ex_done > 0 else "#ef4444"
                                exam_html += f"<div style='flex: 1 1 45%; background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;'><div style='font-size: 0.8rem; color: #64748b; font-weight: bold;'>{ex}</div><div style='font-size: 1rem; color: {c_color}; font-weight: 800;'>{ex_done}/{ex_total}</div></div>"
                        exam_html += "</div>"
                        st.markdown(exam_html, unsafe_allow_html=True)
                    
                    subj_tasks = df_tasks[df_tasks['Subject'] == subj] if not df_tasks.empty else pd.DataFrame()
                    if not subj_tasks.empty:
                        st.markdown("<div style='font-weight:bold; color:#475569; font-size:0.85rem; margin-bottom:8px;'>🎯 مهام المادة:</div>", unsafe_allow_html=True)
                        task_types = subj_tasks['Task Type'].unique()
                        task_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px;'>"
                        for t_type in task_types:
                            t_df = subj_tasks[subj_tasks['Task Type'] == t_type]
                            t_total = len(t_df)
                            t_done = len(t_df[t_df['Status'] == 'Done'])
                            t_color = "#10b981" if t_done == t_total else "#f59e0b" if t_done > 0 else "#ef4444"
                            task_html += f"<div style='flex: 1 1 45%; background: #f0fdf4; padding: 6px; border-radius: 6px; border: 1px solid #bbf7d0; text-align: center;'><div style='font-size: 0.75rem; color: #166534; font-weight: bold;'>{t_type}</div><div style='font-size: 0.95rem; color: {t_color}; font-weight: 800;'>{t_done}/{t_total}</div></div>"
                        task_html += "</div>"
                        st.markdown(task_html, unsafe_allow_html=True)

else:
    df_display = df_lectures[df_lectures['Subject'] == selected_subject]

    cc_title, cc_add = st.columns([3, 1], vertical_alignment="center")
    with cc_title:
        st.markdown(f"<h2>⚡ إدارة: <span style='color:#2563eb;'>{selected_subject}</span></h2>", unsafe_allow_html=True)
    
    with cc_add:
        with st.popover("➕ إضافة محاضرة / امتحان جديد", use_container_width=True):
            st.markdown("**إضافة محتوى جديد لهذه المادة:**")
            with st.form(f"add_lec_form", clear_on_submit=True):
                new_lec_title = st.text_input("اسم المحاضرة / الموضوع")
                
                all_known_exams = [e for e in df_lectures['Exam'].unique() if str(e).strip() != ""]
                if "Unassigned" not in all_known_exams: all_known_exams.append("Unassigned")
                
                new_lec_exam = st.selectbox("الامتحان التابع له", all_known_exams + ["➕ امتحان جديد (كتابة يدوية)..."])
                custom_exam_name = ""
                if new_lec_exam == "➕ امتحان جديد (كتابة يدوية)...":
                    custom_exam_name = st.text_input("اكتب اسم الامتحان (مثال: Quiz 1, OSPE)")
                
                if st.form_submit_button("حفظ المحاضرة", use_container_width=True):
                    final_exam_name = custom_exam_name if new_lec_exam == "➕ امتحان جديد (كتابة يدوية)..." else new_lec_exam
                    if new_lec_title and final_exam_name:
                        new_row = []
                        headers = df_lectures.columns.tolist()
                        for col in headers:
                            if col == 'Subject': new_row.append(selected_subject)
                            elif col == 'Exam': new_row.append(final_exam_name)
                            elif col in ['Lecture Title', 'Title']: new_row.append(new_lec_title)
                            elif col == 'Status': new_row.append('Not Started')
                            elif col == 'Note': new_row.append('')
                            else: new_row.append('')
                        tracker_sheet.append_row(new_row)
                        get_google_data.clear()
                        st.rerun()
                    else:
                        st.error("يرجى تعبئة كافة الحقول.")

    tab1, tab2, tab3 = st.tabs(["📚 خطة الإنجاز", "🎛️ المحرر الشامل", "📈 التحليلات"])

    with tab1:
        active_exams = df_display['Exam'].unique().tolist()
        active_exams = [e for e in active_exams if str(e).strip() != ""]
        if 'Unassigned' in active_exams:
            active_exams.remove('Unassigned')
            active_exams.append('Unassigned') 
            
        for i in range(0, len(active_exams), 3):
            chunk = active_exams[i:i+3]
            cols = st.columns(len(chunk))
            
            for col, exam_key in zip(cols, chunk):
                with col:
                    with st.container(border=True):
                        # 🌟 التعديل الجذري: خلفية وترويسة احترافية جداً للامتحانات 🌟
                        bg_color, border_color, text_color = exam_colors.get(exam_key, default_exam_color)
                        
                        st.markdown(f"""
                        <div style='background-color:{bg_color}; border: 2px solid {border_color}; padding:20px; border-radius:12px; text-align:center; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                            <h3 style='margin:0; color:{text_color}; font-weight:900; font-size: 1.5rem;'>{exam_key}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        exam_date_str = ""
                        row_idx_in_e = -1
                        if not df_exams.empty:
                            match_date = df_exams[(df_exams['Subject'] == selected_subject) & (df_exams['Exam'] == exam_key)]
                            if not match_date.empty:
                                exam_date_str = str(match_date.iloc[0]['Date']).strip()
                                row_idx_in_e = match_date.index[0]
                        
                        with st.popover("📅 ضبط تاريخ الامتحان", use_container_width=True):
                            with st.form(f"date_form_{exam_key}"):
                                new_date = st.date_input("اختر تاريخ الامتحان")
                                if st.form_submit_button("حفظ التاريخ", use_container_width=True):
                                    if exams_sheet is None:
                                        st.warning("هناك مشكلة في إنشاء ورقة 'Exam Dates'.")
                                    else:
                                        if row_idx_in_e != -1:
                                            exams_sheet.update_cell(int(row_idx_in_e) + 2, 3, str(new_date))
                                        else:
                                            exams_sheet.append_row([selected_subject, exam_key, str(new_date)])
                                        get_google_data.clear()
                                        st.rerun()

                        if exam_date_str:
                            try:
                                e_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
                                diff = (e_date - datetime.now().date()).days
                                if diff > 0:
                                    st.markdown(f"<div style='background:#fffbeb; color:#d97706; padding:12px; border-radius:8px; text-align:center; font-weight:bold; font-size:1.1rem; margin-bottom:15px; border:1px solid #fcd34d;'>⏳ باقي {diff} يوم<br><span style='font-size:0.85rem; font-weight:normal;'>{exam_date_str}</span></div>", unsafe_allow_html=True)
                                elif diff == 0:
                                    st.markdown(f"<div style='background:#fef2f2; color:#ef4444; padding:12px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px; border:1px solid #fca5a5;'>🚨 الامتحان اليوم! بالتوفيق.</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<div style='background:#f8fafc; color:#64748b; padding:12px; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:15px; border:1px solid #e2e8f0;'>✅ انتهى الامتحان ({exam_date_str})</div>", unsafe_allow_html=True)
                            except: pass
                                
                        exam_df = df_display[df_display['Exam'] == exam_key]
                        total_e = len(exam_df)
                        done_e = len(exam_df[exam_df['Status'].isin(['Done', 'Uploaded'])])
                        not_done_df = exam_df[~exam_df['Status'].isin(['Done', 'Uploaded'])]
                        
                        st.markdown(f"<div style='text-align:left; color:#64748b; font-size:0.9rem; font-weight:bold; margin-bottom:5px;'>الإنجاز: {done_e} / {total_e}</div>", unsafe_allow_html=True)
                        st.progress(done_e / total_e if total_e > 0 else 0)
                        
                        if done_e == total_e and total_e > 0:
                            st.markdown(f"<div style='background:#ecfdf5; color:#10b981; padding:8px; border-radius:6px; text-align:center; font-weight:bold; margin-bottom:15px; border:1px solid #6ee7b7;'>🏆 جاهز 100%!</div>", unsafe_allow_html=True)
                        else:
                            if not not_done_df.empty:
                                with st.expander("⚠️ المحاضرات المتبقية"):
                                    for _, nd_row in not_done_df.iterrows():
                                        nd_title = nd_row.get('Lecture Title', nd_row.get('Title', ''))
                                        st.markdown(f"<div style='color:#ef4444; font-size:0.9rem; margin-bottom:4px;'>🔴 {nd_title}</div>", unsafe_allow_html=True)
                        
                        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
                        st.markdown("<div style='font-weight:700; color:#475569; margin-bottom:10px;'>📚 المحاضرات:</div>", unsafe_allow_html=True)

                        for idx, row in exam_df.iterrows():
                            status_val = str(row.get('Status', 'Not Started')).strip()
                            if status_val == 'Uploaded' or status_val == '': 
                                status_val = 'Done' if status_val == 'Uploaded' else 'Not Started'
                            if status_val not in status_map: status_val = 'Not Started'

                            st_info = status_map.get(status_val, status_map['Not Started'])
                            l_title = row.get('Lecture Title', row.get('Title', 'بدون عنوان'))
                            
                            expander_title = f"{st_info['icon']} 【 {st_info['label']} 】 {l_title}"
                            
                            with st.expander(expander_title):
                                new_stat = st.selectbox("تحديث الحالة:", list(status_map.keys()), index=list(status_map.keys()).index(status_val), key=f"sel_{idx}")
                                edit_note = row.get('Note', '')
                                if new_stat == 'To Edit':
                                    edit_note = st.text_area("تعديل/ملاحظات:", value=str(edit_note), key=f"note_{idx}")
                                    
                                if st.button("حفظ التغيير ✅", key=f"btn_{idx}", use_container_width=True):
                                    df_lectures.at[idx, 'Status'] = new_stat
                                    df_lectures.at[idx, 'Note'] = edit_note if new_stat == 'To Edit' else ""
                                    tracker_sheet.clear()
                                    tracker_sheet.update(range_name='A1', values=[df_lectures.columns.values.tolist()] + df_lectures.fillna("").values.tolist())
                                    st.success("تم التحديث!")
                                    st.rerun()

        st.markdown("<hr style='border: 1px dashed #cbd5e1; margin: 30px 0;'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#1e293b;'>🛠️ مهام إضافية لـ {selected_subject}</h3>", unsafe_allow_html=True)
        
        if tasks_sheet is not None:
            subject_tasks = df_tasks[df_tasks['Subject'] == selected_subject]
            c1, c2, c3 = st.columns(3)
            
            def render_task_column(col_obj, task_type, type_color, type_bg, icon):
                with col_obj:
                    st.markdown(f"<div style='background:{type_bg}; padding:12px; border-radius:8px; border-top:4px solid {type_color}; margin-bottom:12px;'><b style='font-size:1.1rem; color:{type_color};'>{icon} {task_type}</b></div>", unsafe_allow_html=True)
                    type_tasks = subject_tasks[subject_tasks['Task Type'].astype(str).str.strip() == task_type]
                    
                    pending = type_tasks[type_tasks['Status'] != 'Done']
                    for idx, t_row in pending.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align:right;'><b style='color:#1e293b;'>{t_row['Task Name']}</b></div>", unsafe_allow_html=True)
                            if str(t_row.get('Note', '')).strip(): 
                                st.markdown(f"<div style='text-align:right; color:#64748b; font-size:0.85rem; margin-top:3px;'>📝 {t_row['Note']}</div>", unsafe_allow_html=True)
                            
                            c_btn, c_edit = st.columns(2)
                            if c_btn.button("✅ إنجاز", key=f"done_{idx}", use_container_width=True):
                                tasks_sheet.update_cell(idx + 2, 4, 'Done') 
                                get_google_data.clear()
                                st.rerun()
                            with c_edit.popover("✏️ تعديل", use_container_width=True):
                                with st.form(f"edit_task_{idx}"):
                                    new_name = st.text_input("الاسم", value=t_row['Task Name'])
                                    new_note = st.text_area("الملاحظة", value=str(t_row.get('Note', '')))
                                    if st.form_submit_button("حفظ", use_container_width=True):
                                        tasks_sheet.update_cell(idx + 2, 3, new_name)
                                        tasks_sheet.update_cell(idx + 2, 5, new_note) 
                                        get_google_data.clear()
                                        st.rerun()
                    
                    completed = type_tasks[type_tasks['Status'] == 'Done']
                    if not completed.empty:
                        with st.expander(f"📦 المنجزة ({len(completed)})"):
                            for idx, t_row in completed.iterrows():
                                st.markdown(f"<div style='text-align:right;'><span style='text-decoration: line-through; color:#94a3b8;'>{t_row['Task Name']}</span></div>", unsafe_allow_html=True)
                                if st.button("↩️ تراجع", key=f"undo_{idx}", use_container_width=True):
                                    tasks_sheet.update_cell(idx + 2, 4, 'Pending')
                                    get_google_data.clear()
                                    st.rerun()
                    
                    with st.popover(f"➕ إضافة {task_type}", use_container_width=True):
                        with st.form(f"add_{task_type}"):
                            t_name = st.text_input("الاسم")
                            t_note = st.text_area("ملاحظات (اختياري)")
                            if st.form_submit_button("حفظ إضافة", use_container_width=True) and t_name:
                                tasks_sheet.append_row([selected_subject, task_type, t_name, 'Pending', t_note])
                                get_google_data.clear()
                                st.rerun()

            render_task_column(c1, 'ملخص', '#3b82f6', '#eff6ff', '📑')
            render_task_column(c2, 'أسئلة', '#22c55e', '#f0fdf4', '📝')
            render_task_column(c3, 'مراجعة', '#f59e0b', '#fffbeb', '🔥')

    with tab2:
        edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True)
        if st.button("💾 مزامنة التعديلات", use_container_width=True):
            df_lectures.update(edited_df)
            tracker_sheet.clear()
            tracker_sheet.update(range_name='A1', values=[df_lectures.columns.values.tolist()] + df_lectures.fillna("").values.tolist())
            st.success("تمت المزامنة!")

    with tab3:
        if not df_display.empty:
            st.plotly_chart(px.pie(df_display, names='Status', hole=0.7, title="الإحصائيات"), use_container_width=True)
