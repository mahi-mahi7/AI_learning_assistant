import streamlit as st
import openai
from datetime import datetime
import sqlite3
import json
from cryptography.fernet import Fernet
import os

# 鍵の生成と保存（初回のみ実行）
# key = Fernet.generate_key()
# with open("secret.key", "wb") as key_file:
#     key_file.write(key)

# 鍵の読み込み
fernet_key = os.environ.get('FERNET_KEY')
if fernet_key:
    fernet = Fernet(fernet_key.encode())
else:
    raise ValueError("FERNET_KEY not found in environment variables")


# パスワード確認機能
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    password = st.text_input("パスワードを入力してください", type="password")
    if password == st.secrets["password"]:
        st.session_state.password_correct = True
        return True
    else:
        st.error("パスワードが間違っています")
        return False

# 暗号化関数
def encrypt_data(data):
    return fernet.encrypt(data.encode()).decode()

# 復号化関数
def decrypt_data(encrypted_data):
    return fernet.decrypt(encrypted_data.encode()).decode()

# メイン処理
if check_password():
    # OpenAI APIキーの設定
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
                 (username TEXT, function TEXT, problem TEXT, user_answer TEXT, ai_feedback TEXT, user_question TEXT, ai_response TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations
                 (username TEXT, date TEXT, evaluation TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS learning_history
                 (username TEXT, unit TEXT, count INTEGER)''')

    # 既存のテーブルに新しいカラムを追加
    c.execute('''PRAGMA table_info(problems)''')
    columns = [column[1] for column in c.fetchall()]
    if 'user_answer' not in columns:
        c.execute('''ALTER TABLE problems ADD COLUMN user_answer TEXT''')
    if 'ai_feedback' not in columns:
        c.execute('''ALTER TABLE problems ADD COLUMN ai_feedback TEXT''')
    if 'user_question' not in columns:
        c.execute('''ALTER TABLE problems ADD COLUMN user_question TEXT''')
    if 'ai_response' not in columns:
        c.execute('''ALTER TABLE problems ADD COLUMN ai_response TEXT''')

    conn.commit()


    # ... (その他のコードは変更なし)
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
    if 'current_function' not in st.session_state:
        st.session_state.current_function = "問題解決"
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'user_type' not in st.session_state:
        st.session_state.user_type = ""
    if 'ai_feedback' not in st.session_state:
        st.session_state.ai_feedback = None
    if 'user_question' not in st.session_state:
        st.session_state.user_question = None
    if 'ai_response' not in st.session_state:
        st.session_state.ai_response = None
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

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
            model="gpt-4-0613",
            messages=[
                {"role": "system", "content": f"あなたは{st.session_state.learning_stage}向けの算数・数学の先生です。必ず{st.session_state.learning_stage}が十分理解できる漢字や語彙のみを使用することを順守し、具体例を交えてわかりやすく説明してください。文末の表現はすべて「です、ます」口調に統一してください。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def generate_problem(unit, additional_conditions=""):
        prompt = f"{st.session_state.learning_stage}に向けて適切とされる{unit}に関する問題を1つ作成してください。またその際、解答は生成しないでください。ユーザーに指定されない限り、文章題や小数（特に無限小数）が答えになるような問題は生成せず、比較的単純な計算問題を生成するようにしてください。"
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
            c.execute("SELECT * FROM users WHERE username=? AND user_type=?", (encrypt_data(username), user_type))
            user = c.fetchone()
            if user and decrypt_data(user[1]) == password:
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
                c.execute("SELECT * FROM users WHERE username = ?", (encrypt_data(new_username),))
                if c.fetchone():
                    st.error("このユーザー名は既に使用されています。別のユーザー名を選択してください。")
                else:
                    c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)", 
                              (encrypt_data(new_username), encrypt_data(new_password), new_user_type))
                    conn.commit()
                    st.success("登録が完了しました。ログインしてください。")
            except sqlite3.IntegrityError:
                st.error("登録中にエラーが発生しました。もう一度お試しください。")


    # ... (その他のコードは変更なし)
    def main():
        st.title("AI学習支援ツール")
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

        st.session_state.current_function = st.sidebar.selectbox("機能を選択してください", ["問題解決", "問題出題", "適応型問題出題", "学習評価"])

        if st.session_state.current_function == "問題解決":
            problem_solving()
        elif st.session_state.current_function == "問題出題":
            problem_generation()
        elif st.session_state.current_function == "適応型問題出題":
            optimal_problem_generation()
        elif st.session_state.current_function == "学習評価":
            learning_evaluation()

    def teacher_view():
        st.subheader("教師用ダッシュボード")

        # ユーザー選択
        c.execute("SELECT username FROM users WHERE user_type='学習者'")
        users = [row[0] for row in c.fetchall()]
        selected_user = st.selectbox("ユーザーを選択", users)

        # 機能選択
        functions = ["問題解決", "問題出題", "適応型問題出題", "学習評価"]
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
        
        elif selected_function in ["問題出題", "適応型問題出題"]:
            st.subheader(selected_function)
            c.execute("SELECT problem, COALESCE(user_answer, 'No answer yet') as user_answer, COALESCE(ai_feedback, 'No feedback yet') as ai_feedback, COALESCE(user_question, 'No question yet') as user_question, COALESCE(ai_response, 'No response yet') as ai_response FROM problems WHERE username=? AND function=?", (selected_user, selected_function))
            problems = c.fetchall()
            if problems:
                for i, (problem, user_answer, ai_feedback, user_question, ai_response) in enumerate(problems):
                    with st.expander(f"問題 {i+1}"):
                        display_message(f"問題: {problem}", is_user=False)
                        display_message(f"学習者の回答: {user_answer}", is_user=True)
                        display_message(f"AIのフィードバック: {ai_feedback}", is_user=False)
                        if user_question != 'No question yet':
                            display_message(f"学習者の質問: {user_question}", is_user=True)
                            display_message(f"AIの回答: {ai_response}", is_user=False)
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

    def problem_solving():
        st.subheader("問題解決")
        
        st.sidebar.subheader("セッション履歴")
        
        # 新たな質問ボタン
        if st.sidebar.button("新たな質問"):
            st.session_state.current_session = []
            st.rerun()
        
        # セッション履歴の表示
        for i, session in enumerate(st.session_state.sessions):
            first_question = session[0]['content'][:30] if session else "空のセッション"
            if st.sidebar.button(f"{i+1}, {first_question}..."):
                st.session_state.current_session = session
                st.rerun()

        for message in st.session_state.current_session:
            display_message(message['content'], message['role'] == 'user')

        if user_input := st.chat_input("質問を入力してください"):
            st.session_state.current_session.append({"role": "user", "content": user_input})
            display_message(user_input, is_user=True)

            response = generate_response(user_input)
            st.session_state.current_session.append({"role": "assistant", "content": response})
            display_message(response)

            # 最初の質問時にセッションを保存
            if len(st.session_state.current_session) == 2:  # 最初の質問と回答のペア
                st.session_state.sessions.append(st.session_state.current_session)

            c.execute("INSERT INTO sessions (username, function, session) VALUES (?, ?, ?)",
                      (st.session_state.username, st.session_state.current_function, json.dumps(st.session_state.current_session)))
            conn.commit()

            st.rerun()


    def problem_generation():
        st.subheader("問題出題")
        
        if not st.session_state.problem_generated:
            unit = st.selectbox("単元を選択してください", units[st.session_state.learning_stage])
            additional_conditions = st.text_area("問題の詳細な条件を入力してください（任意）")
            
            if st.button("問題を生成"):
                st.session_state.current_problem = generate_problem(unit, additional_conditions)
                st.session_state.problem_generated = True
                st.session_state.conversation_history = []
                st.rerun()
        
        if st.session_state.problem_generated:
            st.write("問題:", st.session_state.current_problem)
            
            user_answer = st.text_input("回答を入力してください")
            
            if st.button("回答を送信"):
                ai_feedback = evaluate_answer(st.session_state.current_problem, user_answer)
                st.session_state.conversation_history.append(("AI", ai_feedback))
                
                c.execute("INSERT INTO problems (username, function, problem, user_answer, ai_feedback) VALUES (?, ?, ?, ?, ?)",
                          (encrypt_data(st.session_state.username), st.session_state.current_function, 
                           encrypt_data(st.session_state.current_problem), encrypt_data(user_answer), encrypt_data(ai_feedback)))
                conn.commit()
                
                if st.session_state.current_problem.split()[0] in st.session_state.learning_history:
                    st.session_state.learning_history[st.session_state.current_problem.split()[0]] += 1
                else:
                    st.session_state.learning_history[st.session_state.current_problem.split()[0]] = 1
                
                c.execute("INSERT OR REPLACE INTO learning_history (username, unit, count) VALUES (?, ?, ?)",
                          (encrypt_data(st.session_state.username), encrypt_data(st.session_state.current_problem.split()[0]), 
                           st.session_state.learning_history[st.session_state.current_problem.split()[0]]))
                conn.commit()
                
                st.rerun()
            
            for role, content in st.session_state.conversation_history:
                display_message(content, role == "User")


    # ... (その他のコードは変更なし)
            if st.session_state.conversation_history:
                user_question = st.text_input("AIの解説に対する質問があれば入力してください")
                
                if st.button("質問を送信"):
                    prompt = f"問題: {st.session_state.current_problem}\n学習者の質問: {user_question}\nこの質問に対して、{st.session_state.learning_stage}の学習者が理解できるように回答してください。"
                    ai_response = generate_response(prompt)
                    st.session_state.conversation_history.append(("User", user_question))
                    st.session_state.conversation_history.append(("AI", ai_response))
                    
                    c.execute("UPDATE problems SET user_question = ?, ai_response = ? WHERE username = ? AND function = ? AND problem = ?",
                              (user_question, ai_response, st.session_state.username, st.session_state.current_function, st.session_state.current_problem))
                    conn.commit()
                    
                    st.rerun()
            
            if st.button("新しい問題を生成"):
                st.session_state.problem_generated = False
                st.rerun()

    def optimal_problem_generation():
        st.subheader("適応型問題出題")
        
        if not st.session_state.learning_history:
            st.write("まだ学習履歴がありません。問題出題機能を使って問題を解いてみましょう。")
            return
        
        if not st.session_state.weak_problem_generated:
            if st.button("弱点に基づいた問題を生成"):
                weak_units = [unit for unit, count in st.session_state.learning_history.items() if count < 3]
                if weak_units:
                    selected_unit = min(st.session_state.learning_history, key=st.session_state.learning_history.get)
                    st.session_state.current_problem = generate_problem(selected_unit, "この単元は学習者の弱点です。より基本的な問題を出題してください。")
                else:
                    selected_unit = max(st.session_state.learning_history, key=st.session_state.learning_history.get)
                    st.session_state.current_problem = generate_problem(selected_unit, "この単元は学習者が得意です。より難しい問題を出題してください。")
                st.session_state.weak_problem_generated = True
                st.session_state.conversation_history = []
                st.rerun()
        
        if st.session_state.weak_problem_generated:
            st.write("問題:", st.session_state.current_problem)
            
            user_answer = st.text_input("回答を入力してください")
            
            if st.button("回答を送信"):
                ai_feedback = evaluate_answer(st.session_state.current_problem, user_answer)
                st.session_state.conversation_history.append(("AI", ai_feedback))
                
                c.execute("INSERT INTO problems (username, function, problem, user_answer, ai_feedback) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.username, st.session_state.current_function, st.session_state.current_problem, user_answer, ai_feedback))
                conn.commit()
                
                st.rerun()
            
            for role, content in st.session_state.conversation_history:
                display_message(content, role == "User")
            
            if st.session_state.conversation_history:
                user_question = st.text_input("AIの解説に対する質問があれば入力してください")
                
                if st.button("質問を送信"):
                    prompt = f"問題: {st.session_state.current_problem}\n学習者の質問: {user_question}\nこの質問に対して、{st.session_state.learning_stage}の学習者が理解できるように回答してください。"
                    ai_response = generate_response(prompt)
                    st.session_state.conversation_history.append(("User", user_question))
                    st.session_state.conversation_history.append(("AI", ai_response))
                    
                    c.execute("UPDATE problems SET user_question = ?, ai_response = ? WHERE username = ? AND function = ? AND problem = ?",
                              (user_question, ai_response, st.session_state.username, st.session_state.current_function, st.session_state.current_problem))
                    conn.commit()
                    
                    st.rerun()
            
            if st.button("新しい問題を生成"):
                st.session_state.weak_problem_generated = False
                st.rerun()

    def learning_evaluation():
        st.subheader("学習評価")
        
        if st.button("学習履歴を分析"):
            evaluation = analyze_learning_history()
            st.write(evaluation)
            st.session_state.evaluation_history.append(evaluation)
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO evaluations (username, date, evaluation) VALUES (?, ?, ?)",
                      (st.session_state.username, now, evaluation))
            conn.commit()



if __name__ == "__main__":
    main()

































































