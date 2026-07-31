from dotenv import load_dotenv

# Loads variables from .env file into environment
load_dotenv()

CG_DEMO_API_KEY = os.getenv("CG_DEMO_API_KEY")
if not CG_DEMO_API_KEY:
    raise RuntimeError("Missing Demo API key in the environment")

CG_PRO_API_KEY = os.getenv("CG_PRO_API_KEY")
if not CG_PRO_API_KEY:
    raise RuntimeError("Missing Pro API key in the environment")

CG_BASIC_API_KEY = os.getenv("CG_BASIC_API_KEY")
if not CG_BASIC_API_KEY:
    raise RuntimeError("Missing Basic API key in the environment")
