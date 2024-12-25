from environs import Env


env = Env()
env.read_env()

MONGODB_URI = env.str("MONGODB_URI")
