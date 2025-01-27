import streamlit as st
import openai
from datetime import datetime
import sqlite3
import json

# OpenAI APIキーの設定
client = openai.OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# SQLiteデータベースの初期化
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, user_type TEXT)''')
c.execute('''PRAGMA table_info(users)''')
columns = [column[1] for column in c.fetchall()]
if 'user_type' not in columns:
    c.execute('''ALTER TABLE users ADD COLUMN user_type TEXT''')

# 新しいテーブルの作成
c.execute('''CREATE TABLE IF NOT EXISTS sessions
             (username TEXT, function TEXT, session TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS problems
             (username TEXT, function TEXT, problem TEXT, user_answer TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS evaluations
             (username TEXT, date TEXT, evaluation TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS learning_history
             (username TEXT, unit TEXT, count INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS help_requests
             (username TEXT, timestamp DATETIME)''')

# 既存のテーブルに user_answer カラムを追加
c.execute('''PRAGMA table_info(problems)''')
columns = [column[1] for column in c.fetchall()]
if 'user_answer' not in columns:
    c.execute('''ALTER TABLE problems ADD COLUMN user_answer TEXT''')

conn.commit()

# セッション状態の初期化
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'learning_stage' not in st.session_state:
    st.session_state.learning_stage = "中学3年生"
if 'learning_history' not in st.session_state:
    st.session_state.learning_history = {}
if 'current_problem' not in st.session_state:
    st.session_state.current_problem = None
if 'problem_generated' not in st.session_state:
    st.session_state.problem_generated = False
if 'weak_problem_generated' not in st.session_state:
    st.session_state.weak_problem_generated = False
if 'sessions' not in st.session_state:
    st.session_state.sessions = []
if 'current_session' not in st.session_state:
    st.session_state.current_session = []
if 'evaluation_history' not in st.session_state:
    st.session_state.evaluation_history = []
if 'teacher_advice' not in st.session_state:
    st.session_state.teacher_advice = {}
if 'current_function' not in st.session_state:
    st.session_state.current_function = "問題解決"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_type' not in st.session_state:
    st.session_state.user_type = ""

# 学習段階に応じた設定
learning_stages = ["小学1年生", "小学2年生", "小学3年生", "小学4年生", "小学5年生", "小学6年生", "中学1年生", "中学2年生", "中学3年生"]

# 単元リスト
units = {
    "小学1年生": ["たし算", "ひき算", "かたち"],
    "小学2年生": ["かけ算", "長さ", "時間"],
    "小学3年生": ["わり算", "小数", "分数"],
    "小学4年生": ["小数", "面積", "角度"],
    "小学5年生": ["分数", "体積", "平均"],
    "小学6年生": ["比", "速さ", "拡大図と縮図"],
    "中学1年生": ["正負の数", "文字と式",  "方程式", "比例と反比例", "平面図形", "空間図形", "資料の分析と活用"],
    "中学2年生": ["式の計算", "連立方程式", "一次関数", "平行と合同", "三角形と四角形", "場合の数と確率"],
    "中学3年生": ["多項式", "平方根", "二次方程式", "関数y=ax^2", "相似な図形", "円", "三平方の定理", "標本調査"],
}

def generate_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"あなたは{st.session_state.learning_stage}向けの算数・数学の先生です。必ず{st.session_state.learning_stage}が十分理解できる漢字や語彙のみを使用することを順守し、具体例を交えてわかりやすく説明してください。文末の表現はすべて「です、ます」口調に統一してください。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def generate_problem(unit, additional_conditions=""):
    prompt = f"{st.session_state.learning_stage}に向けて適切とされる{unit}に関する問題を1つ作成してください。またその際、解答は生成しないでください。問題を作成する場合は必ず、解答を導くために必要な情報を過不足なく明記するよう順守してください。"
    if additional_conditions:
        prompt += f" 追加条件: {additional_conditions}"
    return generate_response(prompt)

def evaluate_answer(problem, user_answer):
    prompt = f"問題: {problem}\n学習者の回答: {user_answer}\nこの回答に対して確実な正誤判定を行い、正解であれば「正解です!」と表示した後に解説を行い、不正解であれば「不正解です」と表示した後に解法のヒントを提供してください。また学習者の回答欄が空白の場合は無回答であるため不正解としてください。文末の表現はすべて「です、ます」口調に統一してください。"
    return generate_response(prompt)

def analyze_learning_history():
    history_summary = ", ".join([f"{unit}: {count}回" for unit, count in st.session_state.learning_history.items()])
    prompt = f"学習履歴: {history_summary}\nこの学習履歴に基づいて、単元ごとに学習者の特に優れている具体的な点、学習者がつまづいている具体的な点、つまづきを克服するための具体的なアドバイスの3つの観点をそれぞれ行を変更して1～2文で説明・提案してください。文末の表現はすべて「です、ます」口調に統一するようにしてください。"
    return generate_response(prompt)

def display_message(message, is_user=False):
    with st.chat_message("user" if is_user else "assistant"):
        st.markdown(message)

def login():
    st.subheader("ログイン")
    username = st.text_input("ユーザー名")
    password = st.text_input("パスワード", type="password")
    user_type = st.selectbox("ユーザータイプ", ["学習者", "教師"])
    if st.button("ログイン"):
        c.execute("SELECT * FROM users WHERE username=? AND password=? AND user_type=?", (username, password, user_type))
        if c.fetchone():
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_type = user_type
            st.success("ログインに成功しました")
            st.rerun()
        else:
            st.error("ユーザー名、パスワード、またはユーザータイプが間違っています")

def register():
    st.subheader("新規登録")
    new_username = st.text_input("新しいユーザー名")
    new_password = st.text_input("新しいパスワード", type="password")
    new_user_type = st.selectbox("ユーザータイプ", ["学習者", "教師"])
    if st.button("登録"):
        try:
            c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
            if c.fetchone():
                st.error("このユーザー名は既に使用されています。別のユーザー名を選択してください。")
            else:
                c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)", (new_username, new_password, new_user_type))
                conn.commit()
                st.success("登録が完了しました。ログインしてください。")
        except sqlite3.IntegrityError:
            st.error("登録中にエラーが発生しました。もう一度お試しください。")

def main():
    st.title("AI学習支援システム")

    if not st.session_state.logged_in:
        action = st.radio("アクションを選択してください", ["ログイン", "新規登録"])
        if action == "ログイン":
            login()
        else:
            register()
    else:
        if st.session_state.user_type == "学習者":
            student_view()
        else:
            teacher_view()

        if st.sidebar.button("ログアウト"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_type = ""
            st.rerun()

def student_view():
    st.session_state.learning_stage = st.sidebar.selectbox("学習段階を選択してください", learning_stages, index=learning_stages.index("中学3年生"))

    st.session_state.current_function = st.sidebar.selectbox("機能を選択してください", ["問題解決", "問題出題", "個別最適問題出題", "学習評価"])

    if st.button("ヘルプを求める"):
        c.execute("INSERT INTO help_requests (username, timestamp) VALUES (?, ?)", 
                  (st.session_state.username, datetime.now()))
        conn.commit()
        st.success("ヘルプリクエストが送信されました。")

    if st.session_state.current_function == "問題解決":
        problem_solving()
    elif st.session_state.current_function == "問題出題":
        problem_generation()
    elif st.session_state.current_function == "個別最適問題出題":
        optimal_problem_generation()
    elif st.session_state.current_function == "学習評価":
        learning_evaluation()

    if st.session_state.username in st.session_state.teacher_advice:
        st.info(f"教師からのアドバイス: {st.session_state.teacher_advice[st.session_state.username]}")

def teacher_view():
    st.subheader("教師用ダッシュボード")

    # ユーザー選択
    c.execute("SELECT username FROM users WHERE user_type='学習者'")
    users = [row[0] for row in c.fetchall()]
    selected_user = st.selectbox("ユーザーを選択", users)

    # 機能選択
    functions = ["問題解決", "問題出題", "個別最適問題出題", "学習評価"]
    selected_function = st.selectbox("機能を選択", functions)

    # ユーザーの活動を表示
    if selected_function == "問題解決":
        st.subheader("問題解決セッション")
        c.execute("SELECT session FROM sessions WHERE username=? AND function=?", (selected_user, selected_function))
        sessions = c.fetchall()
        if sessions:
            for i, session in enumerate(sessions):
                session_data = json.loads(session[0])
                first_question = session_data[0]['content'][:30] if session_data else "空のセッション"
                with st.expander(f"{i+1}, {first_question}..."):
                    for message in session_data:
                        display_message(message['content'], message['role'] == 'user')
        else:
            st.write("このユーザーの問題解決セッションはまだありません。")
    
    elif selected_function in ["問題出題", "個別最適問題出題"]:
        st.subheader(selected_function)
        c.execute("SELECT problem, COALESCE(user_answer, 'No answer yet') as user_answer FROM problems WHERE username=? AND function=?", (selected_user, selected_function))
        problems = c.fetchall()
        if problems:
            for i, (problem, user_answer) in enumerate(problems):
                with st.expander(f"問題 {i+1}"):
                    st.write("問題:", problem)
                    st.write("学習者の回答:", user_answer)
        else:
            st.write(f"このユーザーの{selected_function}履歴はまだありません。")
    
    elif selected_function == "学習評価":
        st.subheader("学習評価履歴")
        c.execute("SELECT date, evaluation FROM evaluations WHERE username=?", (selected_user,))
        evaluations = c.fetchall()
        if evaluations:
            for date, evaluation in evaluations:
                with st.expander(f"{date}: {evaluation[:30]}..."):
                    st.write(evaluation)
        else:
            st.write("このユーザーの学習評価履歴はまだありません。")

    st.subheader("アドバイス入力")
    advice = st.text_input("アドバイス", st.session_state.teacher_advice.get(selected_user, ""))

    if st.button("アドバイスを保存"):
        st.session_state.teacher_advice[selected_user] = advice
        st.success("アドバイスが保存されました")

    st.subheader("ヘルプリクエスト")
    c.execute("SELECT username, timestamp FROM help_requests ORDER BY timestamp DESC")
    help_requests = c.fetchall()
    if help_requests:
        for username, timestamp in help_requests:
            st.write(f"{username} がヘルプを求めています。 (時刻: {timestamp})")
    else:
        st.write("現在、ヘルプリクエストはありません。")

def problem_solving():
    st.subheader("問題解決")
    
    st.sidebar.subheader("セッション履歴")
    for i, session in enumerate(st.session_state.sessions):
        if st.sidebar.button(f"{i+1}, {session[0]['content'][:30]}...", key=f"session_{i}"):
            st.session_state.current_session = session
            st.rerun()

    if st.sidebar.button("新しい質問"):
        st.session_state.current_session = []
        st.rerun()

    for message in st.session_state.current_session:
        display_message(message['content'], message['role'] == 'user')

    with st.form(key='question_form', clear_on_submit=True):
        user_input = st.text_input("質問を入力してください", key="user_input")
        submit_button = st.form_submit_button("送信")

    if submit_button and user_input:
        response = generate_response(user_input)
        st.session_state.current_session.append({"role": "user", "content": user_input})
        st.session_state.current_session.append({"role": "assistant", "content": response})
        
        # セッションをデータベースに保存
        session_json = json.dumps(st.session_state.current_session)
        c.execute("INSERT INTO sessions (username, function, session) VALUES (?, ?, ?)", 
                  (st.session_state.username, "問題解決", session_json))
        conn.commit()
        
        if st.session_state.current_session not in st.session_state.sessions:
            st.session_state.sessions.append(st.session_state.current_session)
        
        st.rerun()

def problem_generation():
    st.subheader("問題出題")
    if not st.session_state.problem_generated:
        unit = st.selectbox("単元を選択してください", units[st.session_state.learning_stage])
        additional_conditions = st.text_input("追加の問題条件（任意）")
        
        if st.button("問題生成"):
            problem = generate_problem(unit, additional_conditions)
            st.session_state.current_problem = problem
            st.session_state.problem_generated = True
            st.session_state.learning_history[unit] = st.session_state.learning_history.get(unit, 0) + 1
            
            # 問題をデータベースに保存
            c.execute("INSERT INTO problems (username, function, problem, user_answer) VALUES (?, ?, ?, ?)", 
                      (st.session_state.username, "問題出題", problem, None))
            conn.commit()
            
            # 学習履歴をデータベースに保存
            c.execute("INSERT OR REPLACE INTO learning_history (username, unit, count) VALUES (?, ?, ?)", 
                      (st.session_state.username, unit, st.session_state.learning_history[unit]))
            conn.commit()
            
            st.rerun()
    else:
        st.write(st.session_state.current_problem)
        user_answer = st.text_input("回答を入力してください")
        if st.button("回答を確認"):
            evaluation = evaluate_answer(st.session_state.current_problem, user_answer)
            st.write(evaluation)
            
            # ユーザーの回答をデータベースに保存
            c.execute("UPDATE problems SET user_answer = ? WHERE username = ? AND function = ? AND problem = ?", 
                      (user_answer, st.session_state.username, "問題出題", st.session_state.current_problem))
            conn.commit()

        if st.button("新しい問題"):
            st.session_state.problem_generated = False
            st.rerun()

def optimal_problem_generation():
    st.subheader("個別最適問題出題")
    if not st.session_state.weak_problem_generated:
        if st.button("苦手克服問題に挑戦"):
            weak_unit = max(st.session_state.learning_history, key=st.session_state.learning_history.get)
            problem = generate_problem(weak_unit)
            st.session_state.current_problem = problem
            st.session_state.weak_problem_generated = True
            
            # 問題をデータベースに保存
            c.execute("INSERT INTO problems (username, function, problem, user_answer) VALUES (?, ?, ?, ?)", 
                      (st.session_state.username, "個別最適問題出題", problem, None))
            conn.commit()
            
            st.rerun()
    else:
        st.write(st.session_state.current_problem)
        user_answer = st.text_input("回答を入力してください")
        if st.button("回答を確認"):
            evaluation = evaluate_answer(st.session_state.current_problem, user_answer)
            st.write(evaluation)
            
            # ユーザーの回答をデータベースに保存
            c.execute("UPDATE problems SET user_answer = ? WHERE username = ? AND function = ? AND problem = ?", 
                      (user_answer, st.session_state.username, "個別最適問題出題", st.session_state.current_problem))
            conn.commit()

        if st.button("新しい苦手克服問題に挑戦"):
            st.session_state.weak_problem_generated = False
            st.rerun()

def learning_evaluation():
    st.subheader("学習評価")
    if st.button("学習評価を見る"):
        evaluation = analyze_learning_history()
        st.write(evaluation)
        
        # 評価をデータベースに保存
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO evaluations (username, date, evaluation) VALUES (?, ?, ?)", 
                  (st.session_state.username, current_date, evaluation))
        conn.commit()
        
        st.session_state.evaluation_history.append({
            "date": current_date,
            "evaluation": evaluation
        })

    st.subheader("過去の学習評価")
    for entry in st.session_state.evaluation_history:
        with st.expander(f"{entry['date']}"):
            st.write(entry['evaluation'])

if __name__ == "__main__":
    main()

































































