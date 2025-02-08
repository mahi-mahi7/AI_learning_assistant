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
fernet_key = "YKjHFbJ6i60ThzUXLH_NUtueLb-YR6fW2d1WcmPg1II="
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

    # ユーザープロンプトを保存するテーブル(new 2/8 10:04)
    c.execute('''CREATE TABLE IF NOT EXISTS user_prompts
                (username TEXT, function TEXT, prompt TEXT, PRIMARY KEY (username, function))''')

    # user_promptsテーブルにfunctionカラムが存在するか確認し、存在しない場合は追加
    c.execute('''PRAGMA table_info(user_prompts)''')
    columns = [column[1] for column in c.fetchall()]
    if 'function' not in columns:
        c.execute('''ALTER TABLE user_prompts ADD COLUMN function TEXT''')
    conn.commit()



    
    #セッション分析保存テーブル（new 2/8 8:27）
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (username TEXT, function TEXT, session TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS problems
                 (username TEXT, function TEXT, problem TEXT, user_answer TEXT, ai_feedback TEXT, user_question TEXT, ai_response TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations
                 (username TEXT, date TEXT, evaluation TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS learning_history
                 (username TEXT, unit TEXT, count INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS session_analyses
                 (username TEXT, function TEXT, session_id INTEGER, analysis TEXT)''')

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
    if 'problem_solving_instructions' not in st.session_state:
        st.session_state.problem_solving_instructions = {}


    # 学習段階に応じた設定
    learning_stages = [ "中学1年生", "中学2年生", "中学3年生"]

    # 単元リスト
    units = {
        "中学1年生": ["正負の数", "文字と式",  "方程式", "比例と反比例", "平面図形", "空間図形", "資料の分析と活用"],
        "中学2年生": ["式の計算", "連立方程式", "一次関数", "平行と合同", "三角形と四角形", "場合の数と確率"],
        "中学3年生": ["多項式", "平方根", "二次方程式", "関数y=ax^2", "相似な図形", "円", "三平方の定理", "標本調査"],
    }


    def generate_response(prompt, username="", function=""):
        messages = [
            {"role": "system", "content": st.session_state.global_instruction}
        ]
        # problem_generation_instructionsを初期化
        if 'problem_generation_instructions' not in st.session_state:
            st.session_state.problem_generation_instructions = {}
        
        if function == "問題解決" and username in st.session_state.problem_solving_instructions:
            messages.append({"role": "system", "content": st.session_state.problem_solving_instructions[username]})
        elif function == "問題出題" and username in st.session_state.problem_generation_instructions:
            messages.append({"role": "system", "content": st.session_state.problem_generation_instructions[username]})

        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content





    def generate_problem(unit, additional_conditions=""):
        prompt = f"{st.session_state.learning_stage}に向けて適切とされる{unit}に関する問題を1つ作成してください。その際、解答は生成しないでください。また、できる限り解が整数となる問題を生成するようにしてください。"
        if additional_conditions:
            prompt += f" 追加条件: {additional_conditions}"
        return generate_response(prompt, username=st.session_state.username, function="問題出題")


    def evaluate_answer(problem, user_answer):
        prompt = f"問題: {problem}\n学習者の回答: {user_answer}\nこの回答に対して確実な正誤判定を行い、正解であれば「正解です!」と表示した後に解説を行い、不正解であれば「不正解です」と表示した後に解法のヒントを提供してください。また学習者の回答欄が空白の場合は無回答であるため不正解としてください。文末の表現はすべて「です、ます」口調に統一してください。"
        return generate_response(prompt)

    def analyze_learning_history():
        history_summary = ", ".join([f"{unit}: {count}回" for unit, count in st.session_state.learning_history.items()])
        prompt = f"学習履歴: {history_summary}\nこの学習履歴に基づいて、単元ごとに学習者の特に優れていることや以前に比べてできるようになったことがあればその具体的な点、学習者がつまづいている具体的な点、つまづきを克服するための具体的なアドバイスの3つの観点を明確な根拠と共にそれぞれ行を変更して1～2文で説明・提案してください。文末の表現はすべて「です、ます」口調に統一するようにしてください。"
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
            c.execute("SELECT * FROM users WHERE username=? AND user_type=?", (username, user_type))
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
                c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
                if c.fetchone():
                    st.error("このユーザー名は既に使用されています。別のユーザー名を選択してください。")
                else:
                    c.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)", 
                            (new_username, encrypt_data(new_password), new_user_type))
                    conn.commit()
                    st.success("登録が完了しました。ログインしてください。")
            except sqlite3.IntegrityError:
                st.error("登録中にエラーが発生しました。もう一度お試しください。")


    def main():
        #試作（2/7 13:13）
        if 'global_instruction' not in st.session_state:
            st.session_state.global_instruction = """ あなたは中学生3年生向けの学習支援AIアシスタントです。
 以下の点に注意して応答してください：
1. 中学生3年生が理解できる言葉遣い、漢字、語彙を用いて説明する
2. 300字以内で回答を行う
3. 質問の意図を正確に理解し、的確に回答する
4. 文末の表現はすべて「です、ます」口調で統一する
5.  """
        
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

        st.session_state.current_function = st.sidebar.selectbox("機能を選択してください", ["問題解決", "問題出題", "学習者に応じた問題出題", "学習評価"])

        if st.session_state.current_function == "問題解決":
            problem_solving(username=st.session_state.username)

        elif st.session_state.current_function == "問題出題":
            problem_generation()
        elif st.session_state.current_function == "学習者に応じた問題出題":
            optimal_problem_generation()
        elif st.session_state.current_function == "学習評価":
            learning_evaluation()

    # 教師用ダッシュボード
    def teacher_view():
        st.subheader("教師用ダッシュボード")

        # 全機能共通のインストラクション設定
        st.session_state.global_instruction = st.text_area("全機能共通のインストラクションを設定", st.session_state.global_instruction, height=200)
        if st.button("全機能共通のインストラクションを更新"):
            st.success("全機能共通のインストラクションが更新されました。")

        # ユーザー選択
        c.execute("SELECT username FROM users WHERE user_type='学習者'")
        users = [row[0] for row in c.fetchall()]
        selected_user = st.selectbox("ユーザーを選択", users)

        # 機能選択
        functions = ["問題解決", "問題出題", "学習者に応じた問題出題", "学習評価"]
        selected_function = st.selectbox("機能を選択", functions)

        # 学習者ごとのプロンプト設定
        if selected_function == "問題解決":
            if 'problem_solving_instructions' not in st.session_state:
                st.session_state.problem_solving_instructions = {}

            if selected_user not in st.session_state.problem_solving_instructions:
                # データベースからプロンプトを読み込む
                c.execute("SELECT prompt FROM user_prompts WHERE username=? AND function=?", (selected_user, "問題解決"))
                result = c.fetchone()
                if result:
                    st.session_state.problem_solving_instructions[selected_user] = result[0]
                else:
                    st.session_state.problem_solving_instructions[selected_user] = ""

            st.session_state.problem_solving_instructions[selected_user] = st.text_area(
                f"{selected_user}の問題解決プロンプトを設定",
                st.session_state.problem_solving_instructions[selected_user],
                height=100
            )

            if st.button(f"{selected_user}の問題解決プロンプトを更新"):
                # データベースにプロンプトを保存
                try:
                    c.execute("INSERT OR REPLACE INTO user_prompts (username, function, prompt) VALUES (?, ?, ?)",
                                (selected_user, "問題解決", st.session_state.problem_solving_instructions[selected_user]))
                    conn.commit()
                    st.success(f"{selected_user}の問題解決プロンプトが更新されました。")
                except Exception as e:
                    st.error(f"プロンプトの保存中にエラーが発生しました: {e}")
        
        elif selected_function == "問題出題":
            if 'problem_generation_instructions' not in st.session_state:
                st.session_state.problem_generation_instructions = {}

            if selected_user not in st.session_state.problem_generation_instructions:
                # データベースからプロンプトを読み込む
                c.execute("SELECT prompt FROM user_prompts WHERE username=? AND function=?", (selected_user, "問題出題"))
                result = c.fetchone()
                if result:
                    st.session_state.problem_generation_instructions[selected_user] = result[0]
                else:
                    st.session_state.problem_generation_instructions[selected_user] = ""

            st.session_state.problem_generation_instructions[selected_user] = st.text_area(
                f"{selected_user}の問題出題プロンプトを設定",
                st.session_state.problem_generation_instructions[selected_user],
                height=100
            )

            if st.button(f"{selected_user}の問題出題プロンプトを更新"):
                # データベースにプロンプトを保存
                try:
                    c.execute("INSERT OR REPLACE INTO user_prompts (username, function, prompt) VALUES (?, ?, ?)",
                                (selected_user, "問題出題", st.session_state.problem_generation_instructions[selected_user]))
                    conn.commit()
                    st.success(f"{selected_user}の問題出題プロンプトが更新されました。")
                except Exception as e:
                    st.error(f"プロンプトの保存中にエラーが発生しました: {e}")



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

        
        elif selected_function in ["問題出題", "学習者に応じた問題出題"]:
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


        # セッション分析の表示
        st.subheader(f"{selected_function}セッション分析")

        # データベースからセッション分析を読み込む
        session_analyses = {}
        c.execute("SELECT session_id, analysis FROM session_analyses WHERE username=? AND function=?", (selected_user, selected_function))
        analysis_results = c.fetchall()
        for session_id, analysis in analysis_results:
            session_analyses[session_id] = analysis

        if selected_function == "問題解決":
            c.execute("SELECT rowid, session FROM sessions WHERE username=? AND function=?", (selected_user, selected_function))
            sessions = c.fetchall()
        else:
            c.execute("SELECT rowid, problem, user_answer, ai_feedback, user_question, ai_response FROM problems WHERE username=? AND function=?", (selected_user, selected_function))
            sessions = c.fetchall()

        if sessions:
            for i, session in enumerate(sessions):
                session_id = session[0]  # rowidを使用
                if session_id not in session_analyses:
                    with st.spinner(f"セッション {i+1} の分析中..."):
                        session_data = json.dumps(session[1:])  # rowidを除いたデータをJSONに
                        analysis_prompt = f"以下のセッションデータを分析し、1.学習者の理解状況、2.つまづいているポイントとその要因を根拠と共に簡潔に要約してください:\n{session_data}"
                        analysis = generate_response(analysis_prompt, username=selected_user)
                        session_analyses[session_id] = analysis

                        # データベースにセッション分析を保存
                        c.execute("INSERT INTO session_analyses (username, function, session_id, analysis) VALUES (?, ?, ?, ?)",
                                  (selected_user, selected_function, session_id, analysis))
                        conn.commit()

                with st.expander(f"セッション {i+1} 分析"):
                    st.write(session_analyses[session_id])
        else:
            st.write(f"このユーザーの{selected_function}セッションはまだありません。")


    def problem_solving(username=""):
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

            response = generate_response(user_input, st.session_state.username, "問題解決")
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
                           (st.session_state.username, "問題出題", 
                            st.session_state.current_problem, user_answer, ai_feedback))
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
        st.subheader("学習者に応じた問題出題")
        
        if not st.session_state.learning_history:
            st.write("まだ学習履歴がありません。問題出題機能を使って問題を解いてみましょう。")
            return
        
        if not st.session_state.weak_problem_generated:
            if st.button("学習者に応じた問題を生成"):
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
        
        if st.button("学習評価を実行"):
            evaluation = analyze_learning_history()
            st.write(evaluation)
            
            # 評価を保存
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO evaluations (username, date, evaluation) VALUES (?, ?, ?)",
                    (st.session_state.username, current_date, evaluation))
            conn.commit()
            
            # 学習評価履歴の更新
            if 'evaluation_history' not in st.session_state:
                st.session_state.evaluation_history = []
            st.session_state.evaluation_history.append((current_date, evaluation))
        
        # 学習評価履歴の表示
        st.subheader("学習評価履歴")
        if 'evaluation_history' in st.session_state:
            for date, eval_content in st.session_state.evaluation_history:
                with st.expander(f"{date}: {eval_content[:30]}..."):
                    st.write(eval_content)
        else:
            st.write("まだ学習評価が実行されていません。")



if __name__ == "__main__":
    main()

































































