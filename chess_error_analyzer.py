import streamlit as st
import chess.pgn
import chess.engine
import pandas as pd
from io import StringIO

# === CONFIGURATION ===
STOCKFISH_PATH = "stockfish/stockfish"  # Chemin vers l'exécutable Stockfish

# === PARAMÈTRES UTILISATEUR ===
st.sidebar.title("⚙️ Configuration")
max_games = st.sidebar.number_input("Nombre maximum de parties à analyser", min_value=1, max_value=100, value=20)
analysis_depth = st.sidebar.slider("Profondeur d'analyse (Stockfish)", min_value=8, max_value=20, value=14)
show_errors_only = st.sidebar.checkbox("Afficher seulement les erreurs (delta > 50 cp)", value=True)

# === INTERFACE PRINCIPALE ===
st.set_page_config(page_title="Analyseur d'erreurs d'échecs", layout="wide")
st.title("🌐 Analyseur d'erreurs d'échecs")
st.markdown(
    "Charge un fichier `.pgn`, et l'IA (Stockfish) détecte tes coups suboptimaux et propose des alternatives."
)

# Upload PGN
downloaded = st.file_uploader("📂 Upload ton fichier PGN", type="pgn")

if downloaded:
    pgn_text = downloaded.read().decode("utf-8")
    pgn_io = StringIO(pgn_text)
    games = []
    # Lecture des parties jusqu'à max_games
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None or len(games) >= max_games:
            break
        games.append(game)

    if not games:
        st.error("Aucune partie détectée dans le fichier PGN.")
    else:
        # Lancement du moteur Stockfish
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        st.info(f"{len(games)} parties chargées. Analyse en profondeur {analysis_depth}... ⚙️")

        results = []
        # Parcours des parties
        for idx, game in enumerate(games, start=1):
            board = game.board()
            move_number = 1
            for move in game.mainline_moves():
                board.push(move)
                # Évaluation du coup joué
                info_played = engine.analyse(board, chess.engine.Limit(depth=analysis_depth))
                score_played = info_played["score"].white().score(mate_score=10000)
                board.pop()
                # Meilleur coup selon Stockfish
                info_best = engine.analyse(board, chess.engine.Limit(depth=analysis_depth))
                best_move = info_best["pv"][0]
                score_best = info_best["score"].white().score(mate_score=10000)
                board.push(move)

                # Calcul du delta en centipawns
                delta = None
                if score_played is not None and score_best is not None:
                    delta = score_best - score_played
                # Filtrer et stocker
                if delta is not None and (not show_errors_only or abs(delta) > 50):
                    results.append({
                        "Partie #": idx,
                        "Coup #": move_number,
                        "Coup joué": board.san(move),
                        "Meilleur coup": board.san(best_move),
                        "Écart (cp)": delta
                    })
                move_number += 1

        engine.quit()

        # Affichage des résultats
        df = pd.DataFrame(results)
        if df.empty:
            st.success("Aucune erreur significative détectée selon les critères.")
        else:
            st.subheader("📊 Erreurs et suggestions")
            st.dataframe(df)
            st.subheader("📈 Distribution des écarts")
            st.bar_chart(df["Écart (cp)"])
else:
    st.warning("⬆️ Upload un fichier PGN pour lancer l'analyse.")
