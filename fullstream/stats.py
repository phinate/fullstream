# AUTOGENERATED! DO NOT EDIT! File to edit: 01_stats.ipynb (unless otherwise specified).

__all__ = ['hists_from_nn', 'simple_nn_logpdf', 'hists_from_nn_uncert']

# Cell
import pyhf
pyhf.set_backend(pyhf.tensor.jax_backend())
import numpy as onp
import jax.numpy as np

# Cell
def hists_from_nn(nn, params, sigevents, bkgevents, scale=False, use_jax=True):
    '''Create nn-based binned summary statistics from signal and background events.
    nn should be a predict method that's callable on arguments (data,params), and have a logsoftmax output.'''

    # set some arbitrary scale factors
    # todo change
    sig_sf = 0.02 if scale else 1
    bkg_sf = 0.1 if scale else 1

    sighist = np.sum(np.exp(nn(sigevents,params)),axis=0)*sig_sf
    bkghist = np.sum(np.exp(nn(bkgevents,params)),axis=0)*bkg_sf

    if use_jax:
        return sighist, bkghist
    else:
        return onp.asarray(sighist), onp.asarray(bkghist)

# Cell
def simple_nn_logpdf(nn_pars,nn,pars,data,sig_data,bkg_data,bkg_uncerts,use_jax=False):
        '''Return pyhf.Model.logpdf for a simple two-bin model, containing a signal and background histogram created using hists_from_nn.'''
        tensorlib, _ = pyhf.get_backend()

        sig_hist, bkg_hist = hists_from_nn(nn, nn_pars, sig_data, bkg_data, scale=True, use_jax=use_jax)

        spec = {
        'channels': [
            {
                'name': 'singlechannel',
                'samples': [
                    {
                        'name': 'signal',
                        'data': sig_hist,
                        'modifiers': [
                            {'name': 'mu', 'type': 'normfactor', 'data': None}
                        ],
                    },
                    {
                        'name': 'background',
                        'data': bkg_hist,
                        'modifiers': [
                            {
                                'name': 'uncorr_bkguncrt',
                                'type': 'shapesys',
                                'data': bkg_hist,
                            }
                        ],
                    },
                ],
            }
        ]
    }
        model = pyhf.Model(spec)
        print(spec)
        data += model.config.auxdata
        data = tensorlib.astensor(data)
        pars = tensorlib.astensor(pars)

        # grad only defined for scalar output functions, not [scalar]
        return model.logpdf(pars,data)[0]

# Cell
def hists_from_nn_uncert(nn, params, sig, bkg1, bkg2, scale=True, use_jax=True):
    '''Create nn-based binned summary statistics from signal and background events.
    nn should be a predict method that's callable on arguments (data,params), and have a logsoftmax output.'''

    # set some arbitrary scale factors
    # todo change
    sig_sf = 0.02 if scale else 1
    bkg_sf = 0.1 if scale else 1

    sighist = np.sum(np.exp(nn(sig,params)),axis=0)*sig_sf
    b1 = np.sum(np.exp(nn(bkg1,params)),axis=0)*bkg_sf
    b2 = np.sum(np.exp(nn(bkg2,params)),axis=0)*bkg_sf

    bkghist = np.mean((b1,b2),axis=0)
    bkguncert = np.abs((b1-b2)/2.)
    if use_jax:
        return sighist, bkghist,bkguncert
    else:
        return onp.asarray(sighist), onp.asarray(bkghist)