'''
统一 token 计数和 token 级截断能力。
Context Assembly 只依赖这个接口，不直接依赖 tiktoken。
'''

from typing import Protocol
import tiktoken


class TokenCounter(Protocol):

    def count_text(self, text: str) -> int:
        ...

    def truncate_text(self, text: str, max_tokens: int) -> str:
        ...



class TiktokenTokenCounter:
    def __init__(self,encoding_name:str = "o200k_base") -> None:
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_text(self,text:str) -> int:
        return len(self.encoding.encode(text))

    def truncate_text(self,text:str,max_tokens:int) -> str:
        tokens = self.encoding.encode(text)

        if len( tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)