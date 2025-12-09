import socket
import ssl

from text import Text

class Client:

    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        if "/" not in url:
            url = url + "/"

        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # default port
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        # custom port
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)


    def request(self):
        
        # setting up connection to host
        s = socket.socket(
            # to specify that socket will use IPv4
            family=socket.AF_INET,
            # to specify that socket can send random amount of data
            type=socket.SOCK_STREAM,
            # to specify protocol to be used while setting connection
            proto=socket.IPPROTO_TCP
        )

        s.connect((self.host, self.port))

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # setting up additional info for sending request to host
        request = f"GET {self.path} HTTP/1.0\r\n"
        request += f"Host: {self.host}\r\n"
        # \r\n is put twice at end to tell the server that request has ended
        request += "\r\n"

        # encode into bytes before sending out request
        s.send(request.encode("utf8"))

        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        # gathering headers
        response_headers = {}
        while True:

            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # strategy used while trasmitting data
        assert "transfer-encoding" not in response_headers
        # strategy used while compressing data
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content
