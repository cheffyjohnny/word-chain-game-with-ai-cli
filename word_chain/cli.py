import itertools
import os
import threading
import time
import warnings
from pathlib import Path

# macOS system Python is built against LibreSSL; urllib3 v2 (pulled in by
# `requests`) warns loudly about this on every import. Harmless, just noisy.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import click
from dotenv import load_dotenv

from .ai_client import AiMove, build_ai_client
from .repository import JsonGameRepository
from .service import WIN_TARGETS, GameService
from .words import DIFFICULTIES, load_word_set

load_dotenv()

DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "history.json"


def _with_spinner(label: str, func, *args, **kwargs):
    """Show a spinner while a (potentially slow, network-bound) call runs."""
    done = threading.Event()

    def spin():
        for ch in itertools.cycle("|/-\\"):
            if done.is_set():
                break
            click.echo(f"\r{label} {ch}", nl=False)
            time.sleep(0.1)
        click.echo("\r" + " " * (len(label) + 2) + "\r", nl=False)

    thread = threading.Thread(target=spin)
    thread.start()
    try:
        return func(*args, **kwargs)
    finally:
        done.set()
        thread.join()


@click.group()
@click.option(
    "--data-file",
    type=click.Path(path_type=Path),
    default=DEFAULT_DATA_FILE,
    help="Path to the JSON history file",
)
@click.pass_context
def cli(ctx: click.Context, data_file: Path):
    """Play word chain against an AI opponent."""
    ctx.obj = {
        "word_set": load_word_set(),
        "repo": JsonGameRepository(data_file),
    }


@cli.command()
@click.option(
    "--difficulty",
    type=click.Choice(DIFFICULTIES),
    default="normal",
    help="How aggressively the AI plays (favors easy/hard ending letters).",
)
@click.pass_context
def play(ctx: click.Context, difficulty: str):
    """Start an interactive game. Type 'quit' to end early."""
    word_set = ctx.obj["word_set"]
    repo = ctx.obj["repo"]
    ai_client = build_ai_client(word_set, difficulty)
    service = GameService(ai_client, repo, word_set)
    game_ai_mode = "gemini" if os.getenv("GEMINI_API_KEY") else "offline"
    target = WIN_TARGETS[difficulty]

    if game_ai_mode == "gemini":
        click.echo("🤖 AI opponent: Gemini")
    else:
        click.echo("🎲 AI opponent: offline mode (set GEMINI_API_KEY for AI-powered play)")
    click.echo(f"Difficulty: {difficulty}  (win by giving {target} correct answers)")

    start = service.start_word()
    used = {start}
    chain = [start]
    last_letter = start[-1]
    human_turns = 0
    click.echo(f"\nStarting word: {start}")
    click.echo("One wrong answer ends the game. Type 'quit' to leave early.\n")

    while True:
        word = click.prompt(f"Your word (starts with '{last_letter.upper()}')", prompt_suffix=": ").strip()
        if word.lower() == "quit":
            click.echo("🚪 Game ended early.")
            service.record_game(chain, winner="incomplete", ai_mode=game_ai_mode)
            return

        error = service.validate_human_word(word, last_letter, used)
        if error:
            click.echo(f"💥 {error} — you lose!")
            service.record_game(chain, winner="ai", ai_mode=game_ai_mode)
            return

        word = word.lower()
        used.add(word)
        chain.append(word)
        last_letter = word[-1]
        human_turns += 1

        if human_turns >= target:
            click.echo(f"\n🏆 You gave {target} correct answers — you win!")
            service.record_game(chain, winner="human", ai_mode=game_ai_mode)
            return

        move: AiMove = _with_spinner("🤔 AI is thinking", service.ai_turn, last_letter, used)
        if move.word is None:
            click.echo(f"\n🎉 The AI couldn't find a word starting with '{last_letter.upper()}' — you win!")
            service.record_game(chain, winner="human", ai_mode=game_ai_mode)
            return

        icon = "🤖" if move.source == "gemini" else "🎲"
        click.echo(f"{icon} AI: {move.word}")
        used.add(move.word)
        chain.append(move.word)
        last_letter = move.word[-1]


@cli.command(name="history")
@click.pass_context
def history_cmd(ctx: click.Context):
    """List past games."""
    results = ctx.obj["repo"].list()
    if not results:
        click.echo("No games played yet.")
        return
    for r in results:
        click.echo(f"{r.date}  winner={r.winner}  moves={len(r.chain)}  ai={r.ai_mode}")


if __name__ == "__main__":
    cli()
