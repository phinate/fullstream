# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_makers.ipynb (unless otherwise specified).

__all__ = ['hists_from_nn_three_blobs', 'kde_bins_from_nn_three_blobs', 'kde_bins_from_nn_histosys', 'nn_hepdata_like',
           'nn_histosys']

# Cell
import jax
import jax.scipy as jsc
import jax.numpy as jnp
import numpy as np
from functools import partial

from neos import models

# Cell
def hists_from_nn_three_blobs(predict, NMC = 500, sig_mean = [-1, 1], b1_mean=[2, 2], b2_mean=[-1, -1], LUMI=10, sig_scale = 2, bkg_scale = 10):
    '''
    Uses the nn decision function `predict` to form histograms from signal and background
    data, all drawn from multivariate normal distributions with different means. Two
    background distributions are sampled from, which is meant to mimic the situation in
    particle physics where one has a 'nominal' prediction for a nuisance parameter and then
    an alternate value (e.g. from varying up/down by one standard deviation), which then
    modifies the background pdf. Here, we take that effect to be a shift of the mean of the
    distribution. The value for the background histogram is then the mean of the resulting
    counts of the two modes, and the uncertainty can be quantified through the count
    standard deviation.

    Args:
            predict: Decision function for a parameterized observable. Assumed softmax here.

    Returns:
            hist_maker: A callable function that takes the parameters of the observable,
            then constructs signal, background, and background uncertainty yields.
    '''
    def get_hists(network, s, bs):
        NMC = len(s)
        s_hist = predict(network, s).sum(axis=0) * sig_scale / NMC * LUMI

        b_hists = tuple(
            (predict(network, b).sum(axis=0) * bkg_scale / NMC * LUMI) for b in bs
        )

        b_mean = jax.numpy.mean(jax.numpy.asarray(b_hists), axis=0)
        b_unc = jax.numpy.std(jax.numpy.asarray(b_hists), axis=0)
        results = s_hist, b_mean, b_unc
        return results


    def hist_maker():
        bkg1 = np.random.multivariate_normal(b1_mean, [[1, 0], [0, 1]], size=(NMC,))
        bkg2 = np.random.multivariate_normal(b2_mean, [[1, 0], [0, 1]], size=(NMC,))
        sig = np.random.multivariate_normal(sig_mean, [[1, 0], [0, 1]], size=(NMC,))

        def make(network):
            return get_hists(network, sig, (bkg1,bkg2))

        make.bkg1 = bkg1
        make.bkg2 = bkg2
        make.sig = sig
        return make

    return hist_maker



# Cell
# kde experiment

def kde_bins_from_nn_three_blobs(predict, bins, bandwidth, NMC = 500, sig_mean = [-1, 1], b1_mean=[2, 2], b2_mean=[-1, -1], LUMI=10, sig_scale = 2, bkg_scale = 10):
    '''
    Exactly the same as `hists_from_nn_three_blobs`, but takes in a regression network, and
    forms a kernel density estimate (kde) for the output. The yields are then calculated as
    the integral of the kde's cumulative density function between the bin edges, which should
    be specified using the argument `bins`.

    Args:
            predict: Decision function for a parameterized observable. When evaluated, the
            output should be one number per event, i.e. a regression network or similar.

            bins: Array of bin edges, e.g. np.linspace(0,1,3) defines a two-bin histogram with
            edges at 0, 0.5, 1.

            bandwidth: Float that controls the 'smoothness' of the kde. It's recommended to keep
            this lower than the bin width to avoid oversmoothing the distribution. Going too low
            will cause things to break, as the gradients of the kde become unstable. 0.1*bin_width
            is a good rule of thumb, but we have yet to properly validate this practically.

    Returns:
            hist_maker: A callable function that takes the parameters of the observable,
            then constructs signal, background, and background uncertainty yields.
    '''
    # grab bin edges
    edge_lo   = bins[:-1]
    edge_hi   = bins[1:]

    # get counts from gaussian cdfs centered on each event, evaluated binwise
    def to_hist(events):
        cdf_up = jsc.stats.norm.cdf(edge_hi.reshape(-1,1),loc = events, scale = bandwidth)
        cdf_dn = jsc.stats.norm.cdf(edge_lo.reshape(-1,1),loc = events, scale = bandwidth)
        summed = (cdf_up-cdf_dn).sum(axis=1)
        return summed

    def get_hists(network, s, b1, b2):
        NMC = len(s)
        nn_s, nn_b1, nn_b2 = (
            predict(network, s).ravel(),
            predict(network, b1).ravel(),
            predict(network, b2).ravel(),
        )

        kde_counts = jax.numpy.asarray([
            to_hist(nn_s)* sig_scale / NMC * LUMI,
            to_hist(nn_b1)* bkg_scale / NMC * LUMI,
            to_hist(nn_b2)* bkg_scale / NMC * LUMI,
        ])

        b_mean = jax.numpy.mean(kde_counts[1:], axis=0)
        b_unc = jax.numpy.std(kde_counts[1:], axis=0)
        results = kde_counts[0], b_mean,b_unc
        return results


    def hist_maker():
        bkg1 = np.random.multivariate_normal(b1_mean, [[1, 0], [0, 1]], size=(NMC,))
        bkg2 = np.random.multivariate_normal(b2_mean, [[1, 0], [0, 1]], size=(NMC,))
        sig = np.random.multivariate_normal(sig_mean, [[1, 0], [0, 1]], size=(NMC,))

        def make(network):
            return get_hists(network, sig, bkg1, bkg2)

        make.bkg1 = bkg1
        make.bkg2 = bkg2
        make.sig = sig
        return make

    return hist_maker

# Cell
# kde experiment

def kde_bins_from_nn_histosys(predict, bins, bandwidth, NMC = 500, sig_mean = [-1, 1], b1_mean=[2.5, 2], b_mean=[1, -1], b2_mean=[-2.5, -1.5], LUMI=10, sig_scale = 2, bkg_scale = 10):
    '''
    Exactly the same as `hists_from_nn_three_blobs`, but takes in a regression network, and
    forms a kernel density estimate (kde) for the output. The yields are then calculated as
    the integral of the kde's cumulative density function between the bin edges, which should
    be specified using the argument `bins`.

    Args:
            predict: Decision function for a parameterized observable. When evaluated, the
            output should be one number per event, i.e. a regression network or similar.

            bins: Array of bin edges, e.g. np.linspace(0,1,3) defines a two-bin histogram with
            edges at 0, 0.5, 1.

            bandwidth: Float that controls the 'smoothness' of the kde. It's recommended to keep
            this lower than the bin width to avoid oversmoothing the distribution. Going too low
            will cause things to break, as the gradients of the kde become unstable. 0.1*bin_width
            is a good rule of thumb, but we have yet to properly validate this practically.

    Returns:
            hist_maker: A callable function that takes the parameters of the observable,
            then constructs signal, background, and background uncertainty yields.
    '''
    # grab bin edges
    edge_lo   = bins[:-1]
    edge_hi   = bins[1:]

    # get counts from gaussian cdfs centered on each event, evaluated binwise
    def to_hist(events):
        cdf_up = jsc.stats.norm.cdf(edge_hi.reshape(-1,1),loc = events, scale = bandwidth)
        cdf_dn = jsc.stats.norm.cdf(edge_lo.reshape(-1,1),loc = events, scale = bandwidth)
        summed = (cdf_up-cdf_dn).sum(axis=1)
        return summed

    def get_hists(network, s, b_nom, b_up, b_down):
        NMC = len(s)
        nn_s, nn_b_nom, nn_b_up, nn_b_down = (
            predict(network, s).ravel(),
            predict(network, b_nom).ravel(),
            predict(network, b_up).ravel(),
            predict(network, b_down).ravel(),
        )

        kde_counts = jax.numpy.asarray([
            to_hist(nn_s) * sig_scale / NMC * LUMI,
            to_hist(nn_b_nom) * bkg_scale / NMC * LUMI,
            to_hist(nn_b_up) * bkg_scale / NMC * LUMI,
            to_hist(nn_b_down) * bkg_scale / NMC * LUMI,
        ])

        return kde_counts


    def hist_maker():
        bkg_up = np.random.multivariate_normal(b1_mean, [[1, 0], [0, 1]], size=(NMC,))
        bkg_down = np.random.multivariate_normal(b2_mean, [[1, 0], [0, 1]], size=(NMC,))
        bkg_nom = np.random.multivariate_normal(b_mean, [[1, 0], [0, 1]], size=(NMC,))
        sig = np.random.multivariate_normal(sig_mean, [[1, 0], [0, 1]], size=(NMC,))

        def make(network):
            return get_hists(network, sig, bkg_nom, bkg_up, bkg_down)

        make.bkg_nom = bkg_nom
        make.bkg_up = bkg_up
        make.bkg_down = bkg_down
        make.sig = sig
        return make

    return hist_maker

# Cell
import pyhf
pyhf.set_backend(pyhf.tensor.jax_backend())

from neos import models

def nn_hepdata_like(histogram_maker):
    '''
    Returns a function that constructs a typical 'hepdata-like' statistical model
    with signal, background, and background uncertainty yields when evaluated at
    the parameters of the observable.

    Args:
            histogram_maker: A function that, when called, returns a secondary function
            that takes the observable's parameters as argument, and returns yields.

    Returns:
            nn_model_maker: A function that returns a Model object (either from
            `neos.models` or from `pyhf`) when evaluated at the observable's parameters,
            along with the background-only parameters for use in downstream inference.
    '''
    hm = histogram_maker()

    def nn_model_maker(network):
        s, b, db = hm(network)
#         print(f's={s}, b={b}, db={db}')
#         m = pyhf.simplemodels.hepdata_like(s, b, db) # pyhf model
        m = models.hepdata_like(s, b, db) # neos model
        nompars = m.config.suggested_init()
        bonlypars = jax.numpy.asarray([x for x in nompars])
        bonlypars = jax.ops.index_update(bonlypars, m.config.poi_index, 0.0)
        return m, bonlypars

    nn_model_maker.hm = hm
    return nn_model_maker

# Cell
def nn_histosys(histogram_maker):
    '''
    Returns a function that constructs a HEP statistical model using a 'histosys'
    uncertainty for the background (nominal background, up and down systematic variations)
    when evaluated at the parameters of the observable.

    Args:
            histogram_maker: A function that, when called, returns a secondary function
            that takes the observable's parameters as argument, and returns yields.

    Returns:
            nn_model_maker: A function that returns a Model object (either from
            `neos.models` or from `pyhf`) when evaluated at the observable's parameters,
            along with the background-only parameters for use in downstream inference.
    '''
    hm = histogram_maker()

    def from_spec(yields):

        s, b, bup, bdown = yields

        spec = {
            "channels": [
                {
                    "name": "nn",
                    "samples": [
                        {
                            "name": "signal",
                            "data": s,
                            "modifiers": [
                                {"name": "mu", "type": "normfactor", "data": None}
                            ],
                        },
                        {
                            "name": "bkg",
                            "data": b,
                            "modifiers": [
                                {
                                    "name": "nn_histosys",
                                    "type": "histosys",
                                    "data": {
                                        "lo_data": bdown,
                                        "hi_data": bup,
                                    },
                                }
                            ],
                        },
                    ],
                },
            ],
        }

        return pyhf.Model(spec)



    def nn_model_maker(network):
        yields = hm(network)
        m = from_spec(yields)
        nompars = m.config.suggested_init()
        bonlypars = jax.numpy.asarray([x for x in nompars])
        bonlypars = jax.ops.index_update(bonlypars, m.config.poi_index, 0.0)
        return m, bonlypars
    nn_model_maker.hm = hm
    return nn_model_maker