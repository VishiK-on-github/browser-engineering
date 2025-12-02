from browser_client import BroswerClient

def load(url):
    client = BroswerClient(url)
    body = client.request()
    client.show(body)


if __name__ == "__main__":
    import sys
    load(sys.argv[1])