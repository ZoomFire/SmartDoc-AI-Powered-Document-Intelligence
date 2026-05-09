import streamlit as st
import requests
import pandas as pd

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="SmartDocs AI", layout="wide")

# ---------------- LOGIN ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 Login / Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            try:
                res = requests.post(f"{API}/login", json={"username": u, "password": p})
                if res.json().get("status") == "ok":
                    st.session_state.user = u
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("❌ Invalid login")
            except:
                st.error("❌ Backend not running")

    with tab2:
        u2 = st.text_input("New Username", key="reg_user")
        p2 = st.text_input("New Password", type="password", key="reg_pass")

        if st.button("Register"):
            try:
                res = requests.post(f"{API}/register", json={"username": u2, "password": p2})
                if res.json().get("status") == "ok":
                    st.success("✅ Registered! Now login")
                else:
                    st.error("User already exists")
            except:
                st.error("Backend not running")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Settings")

mode = st.sidebar.selectbox(
    "Summary Type",
    ["Short", "Detailed", "Bullet", "ELI5"]
)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------- TITLE ----------------
st.title(f"🤖 SmartDocs AI — {st.session_state.user}")

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["💬 Chat", "📊 Dashboard"])

# ================== CHAT ==================
with tab1:

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # -------- FILE UPLOAD --------
    uploaded_file = st.file_uploader("📄 Upload File", type=["pdf", "txt"])

    if uploaded_file:
        st.success(f"📁 {uploaded_file.name} uploaded")

        if st.button("🚀 Process Document"):
            with st.spinner("Processing document..."):
                try:
                    res = requests.post(
                        f"{API}/summarize",
                        files={"file": uploaded_file}
                    )

                    if res.status_code == 200:
                        summary = res.json().get("summary", "")
                        st.subheader("📄 Summary")
                        st.write(summary)
                    else:
                        st.error("Failed to process file")

                except Exception as e:
                    st.error(f"Backend error: {str(e)}")

    # -------- CHAT --------
    st.subheader("💬 Ask Questions")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask something about your document...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    f"{API}/ask",
                    json={
                        "question": user_input,
                        "username": st.session_state.user
                    }
                )

                if res.status_code == 200:
                    answer = res.json().get("answer", "No response")
                else:
                    answer = "❌ Error from backend"

            except Exception as e:
                answer = f"❌ {str(e)}"

        st.session_state.messages.append({"role": "assistant", "content": answer})

        with st.chat_message("assistant"):
            st.markdown(answer)

# ================== DASHBOARD ==================
with tab2:

    st.subheader("📊 User Dashboard")

    try:
        res = requests.get(f"{API}/history/{st.session_state.user}")

        if res.status_code != 200:
            st.error("Failed to fetch history")
        else:
            history = res.json().get("history", [])

            if not history:
                st.info("No history yet")
            else:
                df = pd.DataFrame(history)

                # -------- STATS --------
                st.metric("Total Questions", len(df))

                # -------- CHART --------
                st.subheader("📈 Usage Trend")
                st.line_chart(df.index)

                # -------- DOWNLOAD --------
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download History", csv, "history.csv")

                # -------- HISTORY --------
                st.subheader("📜 Chat History")

                for i, row in df.iloc[::-1].iterrows():
                    with st.expander(row["q"][:60]):
                        st.write("**Q:**", row["q"])
                        st.write("**A:**", row["a"])

    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")