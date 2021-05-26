# Python-SoXR
# High quality, one-dimensional sample-rate conversion library for Python.
# Python-SoXR is a Python wrapper of libsoxr.
# https://github.com/dofuuz/python-soxr


import numpy as np

from .cysoxr import CySoxr
from .cysoxr import cysoxr_divide_proc_1d, cysoxr_divide_proc_2d
from .cysoxr import cysoxr_oneshot
from .cysoxr import QQ, LQ, MQ, HQ, VHQ

from .version import version as __version__


# libsoxr locates memory per each channel.
# Too much channels will cause memory error.
_CH_LIMIT = 65536

_CH_EXEED_ERR_STR = 'Channel num({}) out of limit. Should be in [1, %d]' % _CH_LIMIT
_DTYPE_ERR_STR = "Data type must be one of ['float32', 'float64', 'int16', 'int32'] and not {}"
_QUALITY_ERR_STR = "Quality must be one of [QQ, LQ, MQ, HQ, VHQ]"


def _quality_to_enum(q):
    if q in (VHQ, HQ, MQ, LQ, QQ):
        return q

    if type(q) is int:
        raise ValueError(_QUALITY_ERR_STR)

    q = q.lower()
    if q in ('vhq', 'soxr_vhq'):
        return VHQ
    elif q in ('hq', 'soxr_hq'):
        return HQ
    elif q in ('mq', 'soxr_mq'):
        return MQ
    elif q in ('lq', 'soxr_lq'):
        return LQ
    elif q in ('qq', 'soxr_qq'):
        return QQ

    raise ValueError(_QUALITY_ERR_STR)


class ResampleStream():
    ''' Streaming resampler

        Use `ResampleStream` for real-time processing or very long signal.

        Parameters
        ----------
        in_rate : float
            Input sample-rate.
        out_rate : float
            Output sample-rate.
        num_channels : int
            Number of channels.
        dtype : type or str, optional
            Internal data type processed with.
            Should be one of float32, float64, int16, int32.
        quality : int or str, optional
            Quality setting.
            One of `QQ`, `LQ`, `MQ`, `HQ`, `VHQ`.
    '''

    def __init__(self,
                 in_rate: float, out_rate: float, num_channels: int,
                 dtype='float32', quality='HQ'):
        if in_rate <= 0 or out_rate <= 0:
            raise ValueError('Sample rate should be over 0')

        if num_channels < 1 or _CH_LIMIT < num_channels:
            raise ValueError(_CH_EXEED_ERR_STR.format(num_channels))

        # internally uses NumPy sclar types, not dtype
        if type(dtype) != type:
            dtype = np.dtype(dtype).type
        if not dtype in (np.float32, np.float64, np.int16, np.int32):
            raise ValueError(_DTYPE_ERR_STR.format(dtype))

        self._type = dtype
        q = _quality_to_enum(quality)

        self._cysoxr = CySoxr(in_rate, out_rate, num_channels, self._type, q)

    def resample_chunk(self, x, last=False):
        ''' Resample chunk with streaming resampler

        Parameters
        ----------
        x : array_like
            Input array. Input can be 1D(mono) or 2D(frames, channels).
            If input is not `np.ndarray` or not dtype in constructor,
            it will be converted to `np.ndarray` with dtype setting.

        last : bool, optional
            Set True at end of input sequence.

        Returns
        -------
        np.ndarray
            Resampled data.
            Output is np.ndarray with same ndim with input.

        '''
        if type(x) != np.ndarray or x.dtype.type != self._type:
            x = np.asarray(x, dtype=self._type)

        return self._cysoxr.process(x, last)


def resample(x, in_rate: float, out_rate: float, quality='HQ'):
    """ Resample signal

    Parameters
    ----------
    x : array_like
        Input array. Input can be 1D(mono) or 2D(frames, channels).
        If input is not `np.ndarray`, it will be converted to `np.ndarray(dtype='float32')`.
        Its dtype should be one of float32, float64, int16, int32.
    in_rate : float
        Input sample-rate.
    out_rate : float
        Output sample-rate.
    quality : int or str, optional
        Quality setting.
        One of `QQ`, `LQ`, `MQ`, `HQ`, `VHQ`.

    Returns
    -------
    np.ndarray
        Resampled data.
        Output is `np.ndarray` with same ndim and dtype with input.
    """
    if in_rate <= 0 or out_rate <= 0:
        raise ValueError('Sample rate should be over 0')

    if type(x) != np.ndarray:
        x = np.asarray(x, dtype=np.float32)

    if not x.dtype.type in (np.float32, np.float64, np.int16, np.int32):
        raise ValueError(_DTYPE_ERR_STR.format(x.dtype.type))

    q = _quality_to_enum(quality)

    x = np.ascontiguousarray(x)    # make array C-contiguous

    if x.ndim == 1:
        return cysoxr_divide_proc_1d(in_rate, out_rate, x, q)
    elif x.ndim == 2:
        num_channels = x.shape[1]
        if num_channels < 1 or _CH_LIMIT < num_channels:
            raise ValueError(_CH_EXEED_ERR_STR.format(num_channels))

        return cysoxr_divide_proc_2d(in_rate, out_rate, x, q)
    else:
        raise ValueError('Input must be 1-D or 2-D array')


def _resample_oneshot(x, in_rate: float, out_rate: float, quality='HQ'):
    '''
    Resample using libsoxr's `soxr_oneshot()`. Use `resample()` for general use.
    `soxr_oneshot()` becomes slow with long input.
    This function exists for test purpose.
    '''
    return cysoxr_oneshot(in_rate, out_rate, x, _quality_to_enum(quality))
