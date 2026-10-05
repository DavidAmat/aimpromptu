# TODO

## 2. Two hands

So Piano is rendered in two different clips:
- One is for the right hand
- The other is for the left hand  So far in these two repos, we have assumed that we will only have one hand, so everything was kind of simple. Now we want to introduce a new element that is the two hands, and we will always force the second hand to be on the bass clef.


We have 2 notations for writing music:
- matrix notation
- textual notation


The notation of the json will be:

### One-hand case
Keep it as it is, if we receive this, we mean that we are going to simply render a single treble cleff:
```json
"matrix": {
      "format": "binary-coo",
      "shape": [88, 8],
      "rows": [39, 43, 41, 41, 43, 43, 43, 43, 57],
      "cols": [0, 0, 1, 2, 3, 4, 5, 6, 7],
      "onset": [39, 43, 41, -1, 43, -1, -1, -1, 57]
    },
```

### two-hand case
This is the new addition, if we instead see the properties `r_matrix` and `l_matrix` in which "r" stands for right hand (treble cleff) and "l" stands for left-hand (bass cleff) we are going to receive a json like:

```json
"r_matrix": {
      "format": "binary-coo",
      "shape": [88, 8],
      "rows": [39, 43, 41, 41, 43, 43, 43, 43, 57],
      "cols": [0, 0, 1, 2, 3, 4, 5, 6, 7],
      "onset": [39, 43, 41, -1, 43, -1, -1, -1, 57]
    },
"l_matrix": {
      "format": "binary-coo",
      "shape": [88, 8],
      "rows": [29, 29, 29, 29, 23, 23, 23, 23],
      "cols": [0, 1, 2, 3, 4, 5, 6, 7],
      "onset": [29, -1, -1, -1, 23, -1, -1, -1,]
    },
```

see that it is really important that the shape[1] (Pythonic notation, second element of the shape array [88,8], in this case `8`) in `r_matrix` matches the shape[1] in `l_matrix`. This is a requirement because when we write music, we must ensure the time-frames of both left and right hand are aligned so they must be equal, if in total there are 8 time frames (0-7) in right, there should be also 8 time frames in left. Since rows and cols depend on the sparsity of the matrix, it can happen that left hand is silent in the last measures so it will be valid to see in r_matrix a cols like [0,1,2,3,4,5,6,7] but the l_matrix cols being only [0] if there is only 1 note on the left hand, this is why we have this `shape` property, because we know the rest to fill this `8` time frames should be silences in the left hand.

The same rules of rendering the music, the key signatures, etc... apply for this new bass cleff

### Textual notation
Current one-hand notation is
```text
*Do-4 || *Mi-4
*Re-4
Re-4
*Re-4
*Re-4
*Re-4
*Mi-4
Mi-4
Mi-4
Mi-4
*Fa#-5
```

The two hand notation incorporates a __ to separate the left from the right hand.
If we don't find any __ in a line, it means that this timeframe there is no note sounding in the left hand (silence)

```text
*Do-4 || *Mi-4 __ *Do-3
*Re-4 __ *Sol-3
Re-4 __ *Fa#-3 || *La#-3
*Re-4
*Re-4
*Re-4
*Mi-4
Mi-4
Mi-4
Mi-4
*Fa#-5
```

For example in the first time frame:
- `*Do-4 || *Mi-4`: is played by RIGHT hand
- `*Do-3` is played by the LEFT hand