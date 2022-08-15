from threading import Thread

from flask import Flask

web = Flask('')


@web.route('/')
def home():
    return "The Blame Bot's Flask server is running and well!\nCheck console for debug and actual bot status."


def run():
    web.run(host='0.0.0.0', port=8080)


def keep_alive():
    run_thread = Thread(target=run)
    run_thread.start()
