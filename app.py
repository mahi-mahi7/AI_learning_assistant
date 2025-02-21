import streamlit as st
import openai
from datetime import datetime
import sqlite3
import json
from cryptography.fernet import Fernet
import os

# 鍵の読み込み
fernet_key = st.secrets["FERNET_KEY"]
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
                (username TEXT, function TEXT, problem TEXT, solution_process TEXT, user_answer TEXT, ai_feedback TEXT, user_question TEXT, ai_response TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations
                 (username TEXT, date TEXT, evaluation TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS learning_history
                 (username TEXT, unit TEXT, count INTEGER)''')
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
                (username TEXT, 
                function TEXT, 
                problem TEXT, 
                solution_process TEXT,
                user_answer TEXT, 
                ai_feedback TEXT, 
                user_question TEXT, 
                ai_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

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
    if 'weak_problem_selection_state' not in st.session_state:
        st.session_state.weak_problem_selection_state = False
    if 'weak_problem_options' not in st.session_state:
        st.session_state.weak_problem_options = []
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
    
    def evaluate_answer(problem, solution_process, user_answer):
        prompt = f"""問題: {problem}
    学習者の解答過程: {solution_process}
    学習者の最終回答: {user_answer}
    この回答に対して以下の手順で評価を行ってください：
    1. 回答過程の評価：解法の手順が正しいか、計算過程に誤りがないかを確認
    2. 最終回答の評価：導き出された答えが正しいかを確認
    3. フィードバック：
    - 正解の場合：「正解です!」と表示し、問題の解説を提示
    - 不正解の場合：「不正解です」と表示し、どの段階で間違えたのかを指摘し、解法ののヒントを提供（答えに直接つながるものは避ける）
    4. 回答過程または回答が空白の場合は、解法のヒントを提供（答えに直接つながるものは避ける）
    """
        return generate_response(prompt)    

    def analyze_solution_history(username):
        """学習者の解答履歴から弱点を分析する関数"""
        # 問題出題機能での解答履歴を取得
        c.execute("""
            SELECT problem, solution_process, user_answer, ai_feedback 
            FROM problems 
            WHERE username = ? AND function = '問題出題'
            ORDER BY rowid DESC LIMIT 5
        """, (username,))
        history = c.fetchall()
        
        if not history:
            return None, "まだ十分な解答履歴がありません。"
        
        # AIに解答履歴を分析させるプロンプト
        analysis_prompt = f"""
        以下の学習者の回答履歴を分析し、以下の点を特定してください：
        1. 回答過程での主な間違いのパターン
        2. 理解が不足している数学的概念
        3. 克服すべき具体的なポイント
        
        解答履歴：
        {json.dumps(history, ensure_ascii=False, indent=2)}
        
        分析結果を以下のJSON形式で返してください：
        {{
            "weak_points": ["弱点1", "弱点2", ...],
            "concepts": ["要復習の概念1", "要復習の概念2", ...],
            "recommendation": "推奨される問題タイプの説明"
        }}
        """

        analysis_result = generate_response(analysis_prompt)
        try:
            analysis_data = json.loads(analysis_result)
            return analysis_data, None
        except json.JSONDecodeError:
            return None, "分析結果の解析に失敗しました。"
    
    def generate_multiple_optimal_problems(analysis_data=None, count=3):
        """分析結果に基づいて指定された数の最適な問題を生成する関数"""
        problems = []
        for _ in range(count):
            if not analysis_data:
                problem = generate_problem("基礎", "基本的な理解度を確認するための問題を出題してください。")
            else:
                # 弱点と概念を組み合わせて問題生成条件を作成
                weak_points = ", ".join(analysis_data["weak_points"])
                concepts = ", ".join(analysis_data["concepts"])
                
                prompt = f"""
                以下の学習者の特性に基づいて問題を生成してください：
                
                弱点: {weak_points}
                要復習の概念: {concepts}
                推奨: {analysis_data["recommendation"]}
                
                これらの点を克服するのに適した問題を生成してください。
                """
                
                problem = generate_problem("カスタマイズされた問題", prompt)
            problems.append(problem)
        return problems   

    def analyze_learning_history():
        # 問題解決機能の履歴を取得
        c.execute("SELECT session FROM sessions WHERE username = ? AND function = '問題解決' ORDER BY rowid DESC", (st.session_state.username,))
        problem_solving_sessions = c.fetchall()
        
        # 問題出題機能の履歴を取得
        c.execute("""
            SELECT problem, solution_process, user_answer, ai_feedback, user_question, ai_response, function
            FROM problems 
            WHERE username = ? AND (function = '問題出題' OR function = '学習者に応じた問題出題')
            ORDER BY rowid DESC
        """, (st.session_state.username,))
        problem_history = c.fetchall()
        
        # 学習履歴のサマリー作成
        history_summary = ""
        
        # 問題解決セッションの分析
        if problem_solving_sessions:
            problem_solving_content = []
            for session in problem_solving_sessions:
                session_data = json.loads(session[0])
                questions = [msg['content'] for msg in session_data if msg['role'] == 'user']
                problem_solving_content.extend(questions)
            
            history_summary += "【問題解決での質問内容】\n"
            history_summary += "\n".join([f"・{q}" for q in problem_solving_content[:5]])  # 最新5件のみ表示
            history_summary += f"\n\n質問セッション総数: {len(problem_solving_sessions)}件"
        
        # 問題出題履歴の分析
        if problem_history:
            # 問題出題機能の履歴
            standard_problems = [p for p in problem_history if p[6] == '問題出題']
            optimal_problems = [p for p in problem_history if p[6] == '学習者に応じた問題出題']
            
            if standard_problems:
                history_summary += "\n\n【問題出題機能での学習履歴】"
                for problem, solution, answer, feedback, question, response, _ in standard_problems[:3]:  # 最新3件のみ表示
                    history_summary += f"\n・問題: {problem}"
                    history_summary += f"\n  解答過程: {solution}"
                    history_summary += f"\n  回答: {answer}"
                    history_summary += f"\n  フィードバック: {feedback}"
                    if question and response:
                        history_summary += f"\n  追加質問: {question}"
                        history_summary += f"\n  AI回答: {response}"
            
            if optimal_problems:
                history_summary += "\n\n【学習者に応じた問題出題での学習履歴】"
                for problem, solution, answer, feedback, question, response, _ in optimal_problems[:3]:  # 最新3件のみ表示
                    history_summary += f"\n・問題: {problem}"
                    history_summary += f"\n  解答過程: {solution}"
                    history_summary += f"\n  回答: {answer}"
                    history_summary += f"\n  フィードバック: {feedback}"
                    if question and response:
                        history_summary += f"\n  追加質問: {question}"
                        history_summary += f"\n  AI回答: {response}"
            
            # 全体の正解率の計算
            correct_count = sum(1 for _, _, _, feedback, _, _, _ in problem_history if feedback and "正解です" in feedback)
            if len(problem_history) > 0:
                correct_rate = (correct_count / len(problem_history)) * 100
                history_summary += f"\n\n全体の正解率: {correct_rate:.1f}%"
        
        # プロンプト生成
        prompt = f"""以下の学習履歴に基づいて、
    1. 学習者の特に優れている点や成長が見られる点
    2. 学習者がつまづいている点や課題
    3. 課題を克服するための具体的なアドバイス
    の3つの観点について、具体的な根拠を示しながら1～2文で説明・提案してください。

    {history_summary}"""
        
        return generate_response(prompt)    

    def analyze_student_status(username):
        """個々の学習者の学習状況を分析する関数"""
        try:
            # 問題解決と問題出題の履歴を取得
            c.execute("""
                SELECT problem, solution_process, user_answer, ai_feedback 
                FROM problems 
                WHERE username = ? 
                AND (function = '問題出題' OR function = '学習者に応じた問題出題')
                ORDER BY rowid DESC
            """, (username,))
            problem_history = c.fetchall()
            
            # 評価履歴を取得
            c.execute("""
                SELECT evaluation 
                FROM evaluations 
                WHERE username = ? 
                ORDER BY date DESC 
                LIMIT 5
            """, (username,))
            evaluation_history = c.fetchall()
            
            # データが存在しない場合のデフォルト値設定
            if not problem_history:
                problem_history = []
            if not evaluation_history:
                evaluation_history = []
            
            # 正答率の計算
            if problem_history:
                correct_answers = sum(1 for _, _, _, feedback in problem_history if feedback and "正解です" in feedback)
                correct_rate = (correct_answers / len(problem_history)) * 100
            else:
                correct_rate = 0
                
            # 学習状況の評価
            if correct_rate >= 80:
                status = "◎"
            elif correct_rate >= 60:
                status = "○"
            else:
                status = "△"

            # データが少ない場合の特別なメッセージ
            if len(problem_history) == 0:
                summary = "学習履歴なし"
            else:
                # 分析用プロンプト作成
                analysis_prompt = f"""
                以下の学習履歴から、学習者の具体的な学習状況を20文字程度で要約してください。
                
                正答率: {correct_rate}%
                問題履歴数: {len(problem_history)}件
                評価履歴数: {len(evaluation_history)}件
                """
                
                summary = generate_response(analysis_prompt)[:20]
            
            return status, summary, correct_rate
            
        except Exception as e:
            # エラーが発生した場合のデフォルト値を返す
            print(f"Error analyzing student status for {username}: {str(e)}")
            return "－", "データ取得エラー", 0
        
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
            st.session_state.global_instruction = """ あなたは中学生3年生向けの数学科目の学習支援AIアシスタントです。
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


    def teacher_view():
        st.subheader("教師用ダッシュボード")
        
        # サイドバーでビューの選択
        view_type = st.sidebar.radio(
            "表示する情報を選択",
            ["全体管理機能", "個別学習者管理機能"]
        )
        
        # セッション状態の初期化
        if 'show_all_students' not in st.session_state:
            st.session_state.show_all_students = False
        
        if view_type == "全体管理機能":
            if st.session_state.show_all_students:
                st.subheader("学習者の学習状況一覧")
                
                # 学習者一覧を取得
                c.execute("SELECT username FROM users WHERE user_type='学習者'")
                students = [row[0] for row in c.fetchall()]
                
                for student in students:
                    st.markdown(f"### 学習者: {student}")
                    
                    # 問題解決機能の最新データ
                    c.execute("""
                        SELECT session 
                        FROM sessions 
                        WHERE username=? AND function='問題解決' 
                        ORDER BY rowid DESC LIMIT 1
                    """, (student,))
                    problem_solving = c.fetchone()
                    
                    # 問題出題機能の最新データ
                    c.execute("""
                        SELECT problem, solution_process, user_answer, ai_feedback 
                        FROM problems 
                        WHERE username=? AND function IN ('問題出題', '学習者に応じた問題出題')
                        ORDER BY rowid DESC LIMIT 1
                    """, (student,))
                    problem_generation = c.fetchone()
                    
                    # データ分析用のプロンプト作成と分析実行
                    analysis_prompt = f"""
                    以下の学習者の最新の学習データを分析し、学習者ごとの学習の理解度を「◎」「〇」「△」の段階ごとに表したうえで、その判断の根拠となるような学習状況を30字程度で要約してください。形式は「学習理解度:～、具体的な学習状況:～」としてください。：
                    
                    問題解決での活動: {json.dumps(problem_solving) if problem_solving else 'データなし'}
                    問題出題での活動: {json.dumps(problem_generation) if problem_generation else 'データなし'}
                    """
                    
                    analysis = generate_response(analysis_prompt)
                    st.write(analysis)


                # Topに戻るボタン
                if st.button("Topへ戻る"):
                    st.session_state.show_all_students = False
                    st.rerun()
            
            else:
                # 全体管理機能のコード
                if st.button("全学習者の最新の学習状況を分析"):
                    st.session_state.show_all_students = True
                    st.rerun()
                
                # 全体共通のインストラクション設定
                st.subheader("全体共通のインストラクション設定")
                st.session_state.global_instruction = st.text_area(
                    "全機能共通のインストラクションを設定", 
                    st.session_state.global_instruction, 
                    height=200
                )
                if st.button("全機能共通のインストラクションを更新"):
                    st.success("全機能共通のインストラクションが更新されました。")


        else:  # 個別学習者管理機能
            # ユーザー選択
            c.execute("SELECT username FROM users WHERE user_type='学習者'")
            users = [row[0] for row in c.fetchall()]
            selected_user = st.selectbox("ユーザーを選択", users)

        # 機能選択（個別学習者管理機能の中に移動）
        functions = ["問題解決", "問題出題", "学習者に応じた問題出題", "学習評価"]
        selected_function = st.selectbox("機能を選択", functions)

        # selected_userを使用するコード
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
            c.execute("""
                SELECT 
                    problem,
                    COALESCE(solution_process, 'No solution process recorded') as solution_process,
                    COALESCE(user_answer, 'No answer yet') as user_answer,
                    COALESCE(ai_feedback, 'No feedback yet') as ai_feedback,
                    COALESCE(user_question, 'No question yet') as user_question,
                    COALESCE(ai_response, 'No response yet') as ai_response,
                    datetime('now', 'localtime') as timestamp
                FROM problems 
                WHERE username=? AND function=?
                ORDER BY rowid ASC
            """, (selected_user, selected_function))
            problems = c.fetchall()
            
            if problems:
                for i, (problem, solution_process, user_answer, ai_feedback, user_question, ai_response, timestamp) in enumerate(problems):
                    with st.expander(f"問題 {i+1} - {problem[:50]}..."):
                        # 問題と解答過程をカードスタイルで表示
                        st.markdown("### 問題と解答")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**🎯 問題**")
                            st.info(problem)
                        
                        with col2:
                            st.markdown("**📝 解答過程**")
                            st.info(solution_process)
                        
                        # 回答とフィードバックの表示
                        st.markdown("### 回答とフィードバック")
                        col3, col4 = st.columns(2)
                        
                        with col3:
                            st.markdown("**✍️ 最終回答**")
                            st.success(user_answer)
                        
                        with col4:
                            st.markdown("**🤖 AIフィードバック**")
                            st.warning(ai_feedback)
                        
                        # 追加の質問と回答があれば表示
                        if user_question != 'No question yet':
                            st.markdown("### 追加の質問と回答")
                            col5, col6 = st.columns(2)
                            
                            with col5:
                                st.markdown("**❓ 学習者の質問**")
                                st.info(user_question)
                            
                            with col6:
                                st.markdown("**💡 AIの回答**")
                                st.success(ai_response)
                        
                        # 分析データの表示（既存のセッション分析があれば）
                        if hasattr(st.session_state, 'session_analyses'):
                            st.markdown("### 💭 分析")
                            st.text(st.session_state.session_analyses.get(i, "この問題の分析データはまだありません。"))
            else:
                st.warning(f"このユーザーの{selected_function}履歴はまだありません。")
        
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

    def generate_multiple_problems(unit, additional_conditions, count=3):
        """指定された数の問題を生成する関数"""
        problems = []
        for _ in range(count):
            problem = generate_problem(unit, additional_conditions)
            problems.append(problem)
        return problems

    def problem_generation():
        st.subheader("問題出題")
        
        # セッション状態の初期化
        if 'problem_selection_state' not in st.session_state:
            st.session_state.problem_selection_state = False
        if 'problem_options' not in st.session_state:
            st.session_state.problem_options = []
        
        if not st.session_state.problem_generated and not st.session_state.problem_selection_state:
            unit = st.selectbox("単元を選択してください", units[st.session_state.learning_stage])
            additional_conditions = st.text_area("問題の詳細な条件を入力してください（任意）")
            
            if st.button("問題を生成"):
                st.session_state.problem_options = generate_multiple_problems(unit, additional_conditions)
                st.session_state.problem_selection_state = True
                st.rerun()
        
        elif st.session_state.problem_selection_state and not st.session_state.problem_generated:
            st.write("以下の問題から取り組みたい問題を選択してください：")
            for i, problem in enumerate(st.session_state.problem_options):
                if st.button(f"問題 {i+1}: {problem}"):
                    st.session_state.current_problem = problem
                    st.session_state.problem_generated = True
                    st.session_state.problem_selection_state = False
                    st.session_state.conversation_history = []
                    st.rerun()
            
            if st.button("問題を再生成"):
                st.session_state.problem_selection_state = False
                st.rerun()

        if st.session_state.problem_generated:
            st.write("問題:", st.session_state.current_problem)
            
            solution_process = st.text_area("回答の過程（式や考え方）を記入してください")
            user_answer = st.text_input("回答を入力してください")
            
            if st.button("回答を送信"):
                ai_feedback = evaluate_answer(st.session_state.current_problem, solution_process, user_answer)
                st.session_state.conversation_history.append(("AI", ai_feedback))

                c.execute("INSERT INTO problems (username, function, problem, solution_process, user_answer, ai_feedback) VALUES (?, ?, ?, ?, ?, ?)",
                        (st.session_state.username, "問題出題", 
                            st.session_state.current_problem, solution_process, user_answer, ai_feedback))
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
        
        if not st.session_state.weak_problem_generated and not st.session_state.weak_problem_selection_state:
            if st.button("学習者に応じた問題を生成"):
                # 解答履歴を分析
                analysis_data, error = analyze_solution_history(st.session_state.username)
                
                if error:
                    st.session_state.weak_problem_options = generate_multiple_optimal_problems(None)
                else:
                    # 分析に基づいて複数の問題を生成
                    st.session_state.weak_problem_options = generate_multiple_optimal_problems(analysis_data)
                
                st.session_state.weak_problem_selection_state = True
                st.rerun()
                
        elif st.session_state.weak_problem_selection_state and not st.session_state.weak_problem_generated:
            st.write("以下の問題から取り組みたい問題を選択してください：")
            for i, problem in enumerate(st.session_state.weak_problem_options):
                if st.button(f"問題 {i+1}: {problem}"):
                    st.session_state.current_problem = problem
                    st.session_state.weak_problem_generated = True
                    st.session_state.weak_problem_selection_state = False
                    st.session_state.conversation_history = []
                    st.rerun()
            
            if st.button("問題を再生成"):
                st.session_state.weak_problem_selection_state = False
                st.rerun()

        if st.session_state.weak_problem_generated:
            st.write("問題:", st.session_state.current_problem)
            
            solution_process = st.text_area("回答の過程（式や考え方）を記入してください")
            user_answer = st.text_input("回答を入力してください")

            
            if st.button("回答を送信"):
                ai_feedback = evaluate_answer(st.session_state.current_problem, solution_process, user_answer)
                st.session_state.conversation_history.append(("AI", ai_feedback))
                
                c.execute("INSERT INTO problems (username, function, problem, solution_process, user_answer, ai_feedback) VALUES (?, ?, ?, ?, ?, ?)",
                        (st.session_state.username, st.session_state.current_function, st.session_state.current_problem, solution_process, user_answer, ai_feedback))
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
            
            if st.button("新しい問題"):
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

































































