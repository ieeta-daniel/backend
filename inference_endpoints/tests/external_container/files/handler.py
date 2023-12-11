import time
from typing import Dict, List, Any


class EndpointHandler:
    def __init__(self, path=""):
        pass
        # Preload all the elements you are going to need at inference.
        # pseudo:
        # self.model= load_model(path)

    def __call__(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        data args:
            inputs (:obj: `str` | `PIL.Image` | `np.array`)
            kwargs
        Return:
            A :obj:`list` | `dict`: will be serialized and returned
        """

        # pseudo
        # self.model(input)
        return [{"outputs": "Hello World"}]


if __name__ == "__main__":
    handler = EndpointHandler()
    print(handler({"inputs": "Say Hello World"}))

    i = 0
    while True:
        print("Hello World")
        time.sleep(i * 5)
        i += 1
