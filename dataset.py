import numpy as np
import torch
from tqdm import tqdm
from pathlib import Path
import data.utils as utils


class DataLoader(object):
    def __init__(self, base_path='./data/processed'):
        self.vocab = utils.num_to_alpha
        self.char2idx = utils.alpha_to_num

        root = Path(base_path)
        self.chars = np.load(root / 'c.npy').astype('int64')
        self.chars_lens = np.load(root / 'c_len.npy')
        self.strokes = np.load(root / 'x.npy').astype('float32')
        self.stroke_lens = np.load(root / 'x_len.npy')

        self.chars_mask = np.zeros_like(self.chars).astype('float32')
        self.strokes_mask = np.zeros(self.strokes.shape[:2]).astype('float32')
        for i, (char_len, stk_len) in enumerate(zip(self.chars_lens, self.stroke_lens)):
            self.chars_mask[i, :char_len] = 1.
            self.strokes_mask[i, :stk_len] = 1.

        idxs = list(zip(np.arange(len(self.stroke_lens)), self.stroke_lens))
        np.random.seed(111)
        np.random.shuffle(idxs)

        self.idxs = {}
        # self.idxs['train'] = list(zip(*sorted(
        #     idxs[:int(len(idxs) * .9)], key=lambda tup: tup[1],
        #     reverse=True
        # )))
        # self.idxs['test'] = list(zip(*sorted(
        #     idxs[int(len(idxs) * .9):], key=lambda tup: tup[1],
        #     reverse=True
        # )))
        self.idxs['train'] = list(zip(
            *idxs[:int(len(idxs) * .9)]
        ))
        self.idxs['test'] = list(zip(
            *idxs[int(len(idxs) * .9):]
        ))

    def sent_to_idx(self, chars):
        return ''.join([chr(self.vocab[x]) for x in chars])

    def create_iterator(self, split='train', batch_size=64, seq_len=100):
        idxs, stk_lengths = [np.array(x) for x in self.idxs[split]]
        for i in range(0, len(idxs), batch_size):
            max_stk_len = max(stk_lengths[i:i + batch_size])
            max_char_len = max(self.chars_lens[idxs[i:i + batch_size]])

            stk = torch.from_numpy(
                self.strokes[idxs[i:i + batch_size]][:, :max_stk_len]
            )
            stk_mask = torch.from_numpy(
                self.strokes_mask[idxs[i:i + batch_size]][:, :max_stk_len]
            )

            chars = torch.from_numpy(
                self.chars[idxs[i:i + batch_size]][:, :max_char_len]
            )
            chars_mask = torch.from_numpy(
                self.chars_mask[idxs[i:i + batch_size]][:, :max_char_len]
            )

            lengths, idx = torch.sort(chars_mask.sum(-1), 0, descending=True)
            stk = stk[idx].cuda()
            stk_mask = stk_mask[idx].cuda()
            chars = chars[idx].cuda()
            chars_mask = chars_mask[idx].cuda()

            chars, chars_mask, stk, stk_mask = [
                x.cuda() for x in [chars, chars_mask, stk, stk_mask]
            ]

            for j in range(1, max_stk_len, seq_len):
                yield j == 1, chars, chars_mask, stk[:, j-1:j + seq_len], stk_mask[:, j-1:j + seq_len]


if __name__ == '__main__':
    dataset = DataLoader()
    itr = dataset.create_iterator('train', batch_size=16)
    for i, data in tqdm(enumerate(itr)):
        if i == 0:
            for x in data[1:]:
                print(x.shape)
