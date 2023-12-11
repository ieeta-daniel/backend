from typing import Dict, List, Any
from torch import no_grad, device, cuda
from transformers import RobertaForSequenceClassification, RobertaTokenizer


class EndpointHandler:
    def __init__(self, path=""):
        pass
        # Preload all the elements you are going to need at inference.
        # pseudo:
        # self.model= load_model(path)

        """
        Paper: https://arxiv.org/abs/2301.07597
        Hub: https://huggingface.co/Hello-SimpleAI/chatgpt-detector-roberta
        """
        # uses GPU if available
        self.device = device('cuda' if cuda.is_available() else 'cpu')

        self.model = RobertaForSequenceClassification.from_pretrained("Hello-SimpleAI/chatgpt-detector-roberta").to(
            self.device)
        self.tokenizer = RobertaTokenizer.from_pretrained("Hello-SimpleAI/chatgpt-detector-roberta")

    def __call__(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        data args:
            inputs (:obj: `str` | `PIL.Image` | `np.array`)
            kwargs
        Return:
            A :obj:`list` | `dict`: will be serialized and returned
        """

        inputs = data.get('inputs', '')  # Assuming 'inputs' key contains the text data

        # Tokenize input text
        input_texts = inputs if isinstance(inputs, List) else [inputs]
        input_ids = self.tokenizer(input_texts, padding="longest", return_tensors="pt").input_ids.to(self.device)

        # Perform inference
        with no_grad():
            logits = self.model(input_ids, attention_mask=input_ids.ne(self.tokenizer.pad_token_id))[0]
            probs = logits.softmax(dim=-1)  # first is human, second logit is fake

        # Format the result
        predictions = [{"confidence": float(prob)} for prob in probs[:, 1].detach().cpu().numpy()]

        return predictions
