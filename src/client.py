import socket
import ssl


class URL:

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


    def request(self, payload=None):
        
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

        # determine http method to be used for request
        method = "POST" if payload else "GET"

        # setting up additional info for sending request to host
        request = f"{method} {self.path} HTTP/1.0\r\n"

        if payload:
            length = len(payload.encode("utf8"))
            request += f"Content-Length: {length}"

        request += f"Host: {self.host}\r\n"

        # \r\n is put twice at end to tell the server that request has ended
        request += "\r\n"

        # add payload to request
        if payload: request += payload

        # encode using utf8 encoding to bytes before sending out request
        s.send(request.encode("utf8"))

        # we wrap socket into a file-like object so we can use read data from it
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        # gathering headers
        response_headers = {}

        # read response from server line by line
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
    

    def resolve(self, url):
        """
        returns correct version of url object 
        based on input string
        """

        if "://" in url: return URL(url)

        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)

            url = dir + "/" + url

        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        
        else:
            return URL(self.scheme + "://" + self.host + \
                          ":" + str(self.port) + url)
        
    
    def __str__(self) -> str:
        """
        get str representation of url object
        """

        port_part = ":" + str(self.port)

        if self.scheme == "https" and self.port == 443:
            port_part = ""

        if self.scheme == "http" and self.port == 80:
            port_part = ""

        return self.scheme + "://" + self.host + port_part + self.path