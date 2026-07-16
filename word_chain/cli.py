import os
import warnings
from pathlib import Path

# macOS system Python is built against LibreSSL; urllib3 v2 (pulled in by
# `requests`) warns loudly about this on every import. Harmless, just noisy.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import click
from dotenv import load_dotenv

from .ai_client import build_ai_client
from .repository import JsonGameRepository
from .service import GameService
from .words import load_word_set

load_dotenv()

DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "history.json"


def get_service(data_file: Path = DEFAULT_DATA_FILE) -> GameService:
    word_set = load_word_set()
    ai_client = build_ai_client(word_set)
    repo = JsonGameRepository(data_file)
    return GameService(ai_client, repo, word_set)


@click.group()
@click.pass_context
def cli(ctx: click.Context):
    """Play word chain against an AI opponent."""
    ctx.obj = get_service()


@cli.command()
@click.pass_obj
def play(service: GameService):
    """Start an interactive game. Type 'quit' to end early."""
    if os.getenv("GEMINI_API_KEY"):
        click.echo("🤖 AI opponent: Gemini")
    else:
        click.echo("🎲 AI opponent: offline mode (set GEMINI_API_KEY for AI-powered play)")

    start = service.start_word()
    used = {start}
    chain = [start]
    last_letter = start[-1]
    click.echo(f"\nStarting word: {start}")
    click.echo("Type 'quit' to end the game.\n")

    while True:
        word = click.prompt(f"Your word (starts with '{last_letter.upper()}')", prompt_suffix=": ").strip()
        if word.lower() == "quit":
            click.echo("Game ended.")
            return

        error = service.validate_human_word(word, last_letter, used)
        if error:
            click.echo(f"❌ {error}")
            continue

        word = word.lower()
        used.add(word)
        chain.append(word)
        last_letter = word[-1]

        move = service.ai_turn(last_letter, used)
        if move.word is None:
            click.echo(f"\n🎉 The AI couldn't find a word starting with '{last_letter.upper()}' — you win!")
            service.record_game(chain, winner="human", ai_mode=move.source)
            return

        icon = "🤖" if move.source == "gemini" else "🎲"
        click.echo(f"{icon} AI: {move.word}")
        used.add(move.word)
        chain.append(move.word)
        last_letter = move.word[-1]


@cli.command(name="history")
@click.pass_obj
def history_cmd(service: GameService):
    """List past games."""
    results = service.list_history()
    if not results:
        click.echo("No games played yet.")
        return
    for r in results:
        click.echo(f"{r.date}  winner={r.winner}  moves={len(r.chain)}  ai={r.ai_mode}")


if __name__ == "__main__":
    cli()
