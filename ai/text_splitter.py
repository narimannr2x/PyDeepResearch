from abc import ABC, abstractmethod
from typing import List, Optional
import warnings


class TextSplitter(ABC):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError('Cannot have chunk_overlap >= chunk_size')
    
    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        pass
    
    def create_documents(self, texts: List[str]) -> List[str]:
        documents = []
        for text in texts:
            for chunk in self.split_text(text):
                documents.append(chunk)
        return documents
    
    def split_documents(self, documents: List[str]) -> List[str]:
        return self.create_documents(documents)
    
    def _join_docs(self, docs: List[str], separator: str) -> Optional[str]:
        text = separator.join(docs).strip()
        return None if text == '' else text
    
    def merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs = []
        current_doc = []
        total = 0
        
        for d in splits:
            _len = len(d)
            # Calculate separator length that would be added
            separator_len = len(separator) if current_doc else 0
            
            if total + separator_len + _len > self.chunk_size:
                if total > self.chunk_size:
                    warnings.warn(
                        f"Created a chunk of size {total}, "
                        f"which is longer than the specified {self.chunk_size}"
                    )
                if current_doc:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    # Keep on popping if:
                    # - we have a larger chunk than in the chunk overlap
                    # - or if we still have any chunks and the length is long
                    while (
                        total > self.chunk_overlap or
                        (total + separator_len + _len > self.chunk_size and total > 0)
                    ):
                        if not current_doc:
                            break
                        # Remove the first element and recalculate total
                        removed = current_doc.pop(0)
                        total -= len(removed)
                        # Also remove the separator that was after it (if any)
                        if current_doc:
                            total -= len(separator)
            # Recalculate separator length after potential pops
            separator_len = len(separator) if current_doc else 0
            current_doc.append(d)
            total += separator_len + _len
        
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        
        return docs


class RecursiveCharacterTextSplitter(TextSplitter):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, 
                 separators: List[str] = None): # type: ignore
        super().__init__(chunk_size, chunk_overlap)
        if separators is None:
            self.separators = ['\n\n', '\n', '.', ',', '>', '<', ' ', '']
        else:
            self.separators = separators
    
    def split_text(self, text: str) -> List[str]:
        final_chunks = []
        
        # Get appropriate separator to use
        separator = self.separators[-1] if self.separators else ''
        for s in self.separators:
            if s == '':
                separator = s
                break
            if s in text:
                separator = s
                break
        
        # Now that we have the separator, split the text
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
        
        # Now go merging things, recursively splitting longer texts.
        good_splits = []
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged_text = self.merge_splits(good_splits, separator)
                    final_chunks.extend(merged_text)
                    good_splits = []
                
                if s:  # Only process non-empty strings
                    other_info = self.split_text(s)
                    final_chunks.extend(other_info)
        
        if good_splits:
            merged_text = self.merge_splits(good_splits, separator)
            final_chunks.extend(merged_text)
        
        return final_chunks