import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="Alomari Creator OS", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# CSS - آمن جداً للخطوط بدون إجبار الأيقونات (لتجنب قلتش السهم)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    /* تطبيق الخط بطريقة آمنة لا تؤثر على أيقونات المنصة */
    html, body, p, h1, h2, h3, h4, h5, h6, label, input, textarea, select, button { 
        font-family: 'Tajawal', sans-serif; 
    }
    
    .stApp { background-color: #f4f7fb; }
    h1, h2, h3, h4, h5, h6 { font-weight: 700; color: #1e293b; }
    
    .animate-fade { animation: fadeIn 0.4s ease-out forwards; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    [data-testid="stExpander"] {
        background-color: #ffffff; border-radius: 12px !important; border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 12px;
    }
    
    div[role="radiogroup"] { gap: 0.3rem !important; }
    div[role="radiogroup"] > label {
        background-color: transparent; padding: 10px 15px; border-radius: 8px; cursor: pointer; margin: 0; transition: all 0.2s;
    }
    div[role="radiogroup"] > label:hover { background-color: #e2e8f0; }
    div[role="radiogroup"] > label[aria-checked="true"] { background-color: #eff6ff !important; border-right: 4px solid #3b82f6; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; } 
    div[role="radiogroup"] > label p { font-size: 1.05rem; font-weight: 600; margin: 0; color: #475569; }
    div[role="radiogroup"] > label[aria-checked="true"] p { color: #1e3a8a; font-weight: 800; }

    .profile-box {
        text-align: center; padding: 25px 20px; margin-bottom: 15px; 
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); 
        border-radius: 16px; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.15);
    }
    .profile-box h3 { color: white !important; font-size: 1.4rem !important; margin:0;}
    
    button[data-baseweb="tab"][aria-selected="true"] { 
        color: #2563eb !important; border-bottom: 3px solid #2563eb !important; background-color: #eff6ff !important; border-radius: 8px 8px 0 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# دالة تحويل الوقت إلى نظام 12 ساعة (ص/م)
# ==========================================
def format_to_12hr(time_str):
    if pd.isna(time_str) or str(time_str).strip() == "": return "غير محدد"
    try:
        t = pd.to_datetime(str(time_str)).strftime("%I:%M %p")
        return t.replace("AM", "ص").replace("PM", "م")
    except:
        return str(time_str)

# ==========================================
# 2. الربط مع جوجل شيت (حماية فولاذية للجداول الفارغة)
# ==========================================
@st.cache_resource(ttl=60)
def get_google_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Dashboard")
    
    # 1. المحاضرات
    tracker_sheet = spreadsheet.worksheet("Lectures Tracker")
    records_l = tracker_sheet.get_all_records()
    df_l = pd.DataFrame(records_l) if records_l else pd.DataFrame()
    if not df_l.empty:
        if 'Exam' not in df_l.columns: df_l['Exam'] = 'Unassigned'
        if 'Note' not in df_l.columns: df_l['Note'] = ''
        
    # 2. التقويم
    cal_cols = ["Date", "Time", "Subject", "Note"]
    try:
        cal_sheet = spreadsheet.worksheet("Calendar")
        c_recs = cal_sheet.get_all_records()
        if not c_recs:
            df_c = pd.DataFrame(columns=cal_cols)
            # إنشاء العناوين إذا كان الشيت فارغاً تماماً
            if len(cal_sheet.get_all_values()) == 0:
                cal_sheet.update(range_name='A1', values=[cal_cols])
        else:
            df_c = pd.DataFrame(c_recs)
            for col in cal_cols:
                if col not in df_c.columns: df_c[col] = ""
    except:
        cal_sheet, df_c = None, pd.DataFrame(columns=cal_cols)
        
    # 3. المهام (حل مشكلة KeyError الجذري هنا!)
    tasks_cols = ["Subject", "Task Type", "Task Name", "Status", "Note"]
    try:
        tasks_sheet = spreadsheet.worksheet("Tasks")
        t_recs = tasks_sheet.get_all_records()
        if not t_recs:
            df_t = pd.DataFrame(columns=tasks_cols)
            # إنشاء العناوين إذا كان الشيت فارغاً تماماً
            if len(tasks_sheet.get_all_values()) == 0:
                tasks_sheet.update(range_name='A1', values=[tasks_cols])
        else:
            df_t = pd.DataFrame(t_recs)
            for col in tasks_cols:
                if col not in df_t.columns: df_t[col] = ""
    except:
        tasks_sheet, df_t = None, pd.DataFrame(columns=tasks_cols)
        
    return df_l, df_c, df_t, tracker_sheet, cal_sheet, tasks_sheet

df_lectures, df_calendar, df_tasks, tracker_sheet, cal_sheet, tasks_sheet = get_google_data()

# ==========================================
# 3. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    st.markdown("<div class='profile-box'><h3>👨‍⚕️ محمد العمري</h3><p style='margin:5px 0 0 0; color:#cbd5e1; font-size:1.1rem;'>Creator OS</p></div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b; font-weight:700; margin-bottom:10px; font-size:1rem;'>📂 مساحات العمل</div>", unsafe_allow_html=True)
    if not df_lectures.empty:
        subjects = ["🏠 الصفحة الرئيسية"] + list(df_lectures['Subject'].unique())
        selected_subject = st.radio("القائمة:", subjects, label_visibility="collapsed")
    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    search_query = st.text_input("🔍 بحث سريع عن محاضرة...", "")

# إعدادات الألوان والحالات
status_map = {
    'Done': {'icon': '✅', 'color': '#10b981', 'bg': '#ecfdf5', 'label': 'منجزة'},
    'In Progress': {'icon': '⏳', 'color': '#f59e0b', 'bg': '#fffbeb', 'label': 'قيد العمل'},
    'To Edit': {'icon': '🛠️', 'color': '#ef4444', 'bg': '#fef2f2', 'label': 'تعديل'},
    'Not Started': {'icon': '🔴', 'color': '#64748b', 'bg': '#f8fafc', 'label': 'لم تبدأ'}
}
exam_colors = {
    "First": ("#ecfdf5", "#10b981", "#064e3b"), "Second": ("#f5f3ff", "#8b5cf6", "#4c1d95"),
    "Mid": ("#fffbeb", "#f59e0b", "#78350f"), "Final": ("#eff6ff", "#3b82f6", "#1e3a8a"), "Unassigned": ("#f8fafc", "#64748b", "#334155")
}

# ==========================================
# 4. التوجيه (Routing)
# ==========================================

if selected_subject == "🏠 الصفحة الرئيسية":
    st.markdown("<h2>🏠 لوحة القيادة (Overview)</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.markdown("<h3 style='color:#1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;'>🗓️ الجدول والمواعيد</h3>", unsafe_allow_html=True)
        if cal_sheet is not None:
            with st.expander("⚙️ إضافة أو إدارة المواعيد"):
                st.markdown("**➕ إضافة موعد جديد:**")
                with st.form("add_cal_form_home", clear_on_submit=True):
                    c_date = st.date_input("التاريخ")
                    c_time = st.time_input("الوقت")
                    c_sub = st.text_input("العنوان (مثال: وجاهي أناتومي)")
                    c_note = st.text_area("ملاحظات (اختياري)")
                    if st.form_submit_button("حفظ الموعد"):
                        cal_sheet.append_row([str(c_date), str(c_time), c_sub, c_note])
                        get_google_data.clear()
                        st.rerun()
                
                st.markdown("---")
                st.markdown("**✏️ تعديل أو حذف المواعيد الحالية:**")
                if not df_calendar.empty:
                    for idx, row in df_calendar.iterrows():
                        sub_text = str(row.get('Subject', 'بدون عنوان'))
                        with st.popover(f"📅 {row.get('Date', '')} | {sub_text}", use_container_width=True):
                            with st.form(f"edit_cal_{idx}"):
                                e_date = st.text_input("التاريخ", value=str(row.get('Date', '')))
                                e_time = st.text_input("الوقت", value=str(row.get('Time', '')))
                                e_sub = st.text_input("العنوان", value=sub_text)
                                e_note = st.text_area("ملاحظات", value=str(row.get('Note', '')))
                                
                                c_save, c_del = st.columns(2)
                                if c_save.form_submit_button("💾 حفظ التعديل"):
                                    cal_sheet.update(range_name=f'A{idx+2}:D{idx+2}', values=[[e_date, e_time, e_sub, e_note]])
                                    get_google_data.clear()
                                    st.rerun()
                                if c_del.form_submit_button("🗑️ حذف الموعد"):
                                    cal_sheet.delete_rows(idx + 2)
                                    get_google_data.clear()
                                    st.rerun()

        if not df_calendar.empty:
            for _, row in df_calendar.tail(5).iloc[::-1].iterrows():
                subj_val = str(row.get('Subject', '')).strip() or "📌 موعد بدون عنوان"
                date_val = str(row.get('Date', '')).strip()
                time_val = format_to_12hr(row.get('Time', ''))
                note_val = str(row.get('Note', '')).strip()
                
                note_html = f"<div style='color: #64748b; font-size: 0.9rem; margin-top: 10px; background: #f8fafc; padding: 8px 12px; border-radius: 6px; border-right: 3px solid #cbd5e1;'>📝 {note_val}</div>" if note_val else ""

                st.markdown(f"""
                <div class='animate-fade' style='background: white; border-right: 5px solid #3b82f6; padding: 15px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);'>
                    <div style='color: #1e3a8a; font-weight: 800; font-size: 1.15rem; margin-bottom: 10px;'>{subj_val}</div>
                    <div style='display: flex; gap: 15px; align-items: center;'>
                        <div style='background: #eff6ff; color: #2563eb; padding: 4px 10px; border-radius: 6px; font-size: 0.9rem; font-weight: bold;'>📅 {date_val}</div>
                        <div style='background: #fef2f2; color: #ef4444; padding: 4px 10px; border-radius: 6px; font-size: 0.9rem; font-weight: bold;'>⏰ {time_val}</div>
                    </div>
                    {note_html}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("لا توجد مواعيد وجاهية قادمة.")

    with col2:
        st.markdown("<h3 style='color:#1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;'>🎯 مهام هذا الأسبوع</h3>", unsafe_allow_html=True)
        if df_tasks is not None and not df_tasks.empty:
            pending_tasks = df_tasks[df_tasks['Status'] != 'Done']
            if not pending_tasks.empty:
                for idx, t_row in pending_tasks.iterrows():
                    color = "#f59e0b" if str(t_row['Task Type']).strip() == 'مراجعة' else "#8b5cf6" if str(t_row['Task Type']).strip() == 'ملخص' else "#10b981"
                    st.markdown(f"""
                    <div class='animate-fade' style='background: white; border-right: 5px solid {color}; padding: 15px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); display: flex; flex-direction: column; gap: 5px;'>
                        <div style='font-size: 0.8rem; font-weight: 800; color: {color}; background: #f8fafc; width: fit-content; padding: 3px 10px; border-radius: 20px;'>{t_row['Task Type']}</div>
                        <div style='color: #1e293b; font-weight: 700; font-size: 1.05rem;'>{t_row['Task Name']}</div>
                        <div style='color: #64748b; font-size: 0.9rem; font-weight: 600;'>📚 {t_row['Subject']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("لقد أنجزت كل المهام المعلقة. 🔥")

    st.markdown("<hr style='border: 1px dashed #cbd5e1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#1e293b; margin-bottom: 20px;'>📊 نسبة الإنجاز في المواد</h3>", unsafe_allow_html=True)
    
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
                    <div style='width: 100%; background-color: #e2e8f0; border-radius: 10px; height: 8px; margin-bottom:15px; overflow:hidden;'>
                        <div style='width: {pct}%; background-color: #10b981; height: 100%; border-radius: 10px;'></div>
                    </div>
                    """, unsafe_allow_html=True)
                    for ex in ["First", "Second", "Mid", "Final", "Unassigned"]:
                        ex_df = subj_df[subj_df['Exam'] == ex]
                        if not ex_df.empty:
                            ex_total = len(ex_df)
                            ex_done = len(ex_df[ex_df['Status'].isin(['Done', 'Uploaded'])])
                            c_color = "#10b981" if ex_done == ex_total else "#f59e0b" if ex_done > 0 else "#ef4444"
                            st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:0.95rem; margin-top:5px; padding: 5px; background:#f8fafc; border-radius:5px;'><span>{ex}</span><span style='color:{c_color}; font-weight:bold;'>{ex_done} / {ex_total}</span></div>", unsafe_allow_html=True)

else:
    # فلترة آمنة
    df_display = df_lectures[df_lectures['Subject'] == selected_subject]
    if search_query:
        t_col = 'Lecture Title' if 'Lecture Title' in df_display.columns else 'Title'
        df_display = df_display[df_display[t_col].astype(str).str.contains(search_query, case=False, na=False)]

    st.markdown(f"<h2>⚡ إدارة: <span style='color:#2563eb;'>{selected_subject}</span></h2>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📚 خطة الإنجاز", "🎛️ المحرر الشامل", "📈 التحليلات"])

    with tab1:
        exams = ["First", "Second", "Mid", "Final", "Unassigned"]
        active_exams = [e for e in exams if not df_display[df_display['Exam'] == e].empty]
        cols = st.columns(len(active_exams)) if active_exams else [st.container()]
        
        for col, exam_key in zip(cols, active_exams):
            with col:
                bg_color, border_color, text_color = exam_colors.get(exam_key, ("#f8fafc", "#64748b", "#334155"))
                st.markdown(f"<div style='background-color:{bg_color}; padding:10px; border-radius:8px; border-bottom:4px solid {border_color}; text-align:center; margin-bottom:15px;'><h4 style='margin:0; color:{text_color};'>{exam_key}</h4></div>", unsafe_allow_html=True)
                
                exam_df = df_display[df_display['Exam'] == exam_key]
                for idx, row in exam_df.iterrows():
                    current_status = row.get('Status', 'Not Started')
                    if current_status == 'Uploaded': current_status = 'Done'
                    st_info = status_map.get(current_status, status_map['Not Started'])
                    l_title = row.get('Lecture Title', row.get('Title', 'بدون عنوان'))
                    
                    expander_title = f"{st_info['icon']} 【 {st_info['label']} 】 {l_title}"
                    
                    with st.expander(expander_title):
                        new_stat = st.selectbox("تحديث الحالة:", list(status_map.keys()), index=list(status_map.keys()).index(current_status), key=f"sel_{idx}")
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

        # ==========================================
        # مدير المهام الجديد (مع فلترة آمنة)
        # ==========================================
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
                            st.markdown(f"<b style='color:#1e293b;'>{t_row['Task Name']}</b>", unsafe_allow_html=True)
                            if str(t_row.get('Note', '')).strip(): st.caption(f"📝 {t_row['Note']}")
                            
                            c_btn, c_edit = st.columns(2)
                            if c_btn.button("✅ إنجاز", key=f"done_{idx}", use_container_width=True):
                                tasks_sheet.update_cell(idx + 2, 4, 'Done') 
                                get_google_data.clear()
                                st.rerun()
                            with c_edit.popover("✏️ تعديل", use_container_width=True):
                                with st.form(f"edit_task_{idx}"):
                                    new_name = st.text_input("الاسم", value=t_row['Task Name'])
                                    new_note = st.text_area("الملاحظة", value=str(t_row.get('Note', '')))
                                    if st.form_submit_button("حفظ"):
                                        tasks_sheet.update_cell(idx + 2, 3, new_name)
                                        tasks_sheet.update_cell(idx + 2, 5, new_note) 
                                        get_google_data.clear()
                                        st.rerun()
                    
                    completed = type_tasks[type_tasks['Status'] == 'Done']
                    if not completed.empty:
                        with st.expander(f"📦 المنجزة ({len(completed)})"):
                            for idx, t_row in completed.iterrows():
                                st.markdown(f"<span style='text-decoration: line-through; color:#94a3b8;'>{t_row['Task Name']}</span>", unsafe_allow_html=True)
                                if st.button("↩️ تراجع", key=f"undo_{idx}"):
                                    tasks_sheet.update_cell(idx + 2, 4, 'Pending')
                                    get_google_data.clear()
                                    st.rerun()
                    
                    with st.popover(f"➕ إضافة {task_type}", use_container_width=True):
                        with st.form(f"add_{task_type}"):
                            t_name = st.text_input("الاسم")
                            t_note = st.text_area("ملاحظات (اختياري)")
                            if st.form_submit_button("حفظ إضافة") and t_name:
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
