"""python -m uarb_agent  -> run the email agent."""
import logging
import os

from dotenv import load_dotenv

from .service import Service


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    from agentmail import AgentMail

    client = AgentMail(api_key=os.environ["AGENTMAIL_API_KEY"])
    Service(
        client,
        os.environ["AGENTMAIL_ADDRESS"],
        work_root=os.environ.get("WORK_DIR", "/tmp/uarb"),
        max_per_hour=int(os.environ.get("MAX_REQUESTS_PER_HOUR", "10")),
    ).run_forever()


if __name__ == "__main__":
    main()
