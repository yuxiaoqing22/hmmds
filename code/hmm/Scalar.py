""" Scalar.py: Implements HMMs with discrete observations.

"""
# Copyright (c) 2003, 2007, 2008, 2012 Andrew M. Fraser
import random
import numpy as np

# cum_rand generates random integers from a cumulative distribution
cum_rand = lambda cum: np.searchsorted(cum, random.random())

def initialize(x, shape, dtype=np.float64):
    if x == None or x.shape != shape:
        return np.empty(shape, dtype)
    return x
## ----------------------------------------------------------------------
class Prob(np.ndarray):
    '''Subclass of ndarray for probability matrices.  P[a,b] is the
    probability of b given a.  The class has additional methods and is
    designed to enable alternative implementations with speed
    improvements implemented by uglier code.

    '''
    # See http://docs.scipy.org/doc/numpy/user/basics.subclassing.html
    def assign_col(self, i, col):
        '''
        Replace column of self with data specified by the parameters

        Parameters
        ----------
        i : int
            Column index
        col : array_like
            Column data

        Returns
        -------
        None
        '''
        self[:, i] = col
    def likelihoods(self, v):
        '''likelihoods for vector of data

        Parameters
        ----------
        v : array_like
            Column data

        Returns
        -------
        L : array_like

            Given T = len(v) and self.shape = (M,N), L.shape = (T,M)
            with the interpretation L[t,a] = Prob(v[t]|a)

        '''
        return self[:, v].T
    def inplace_elementwise_multiply(self, a):
        '''
        Multiply self by argument

        Parameters
        ----------
        a : array_like

        Returns
        -------
        None
        '''
        self *= a
    def normalize(self):
        '''
        Make each row a proability that sums to one

        Parameters
        ----------
        None

        Returns
        -------
        None
        '''
        s = self.sum(axis=1)
        for i in range(self.shape[0]):
            self[i, :] /= s[i]
    def step_forward(self, a):
        '''
        Replace values of argument a with matrix product a*self

        Parameters
        ----------
        a : array_like

        Returns
        -------
        None
        '''
        a[:] = np.dot(a, self)
    def step_back(self, a):
        '''
        Replace values of argument a with matrix product self*a

        Parameters
        ----------
        a : array_like

        Returns
        -------
        None
        '''
        a[:] = np.dot(self, a)
    def values(self):
        '''
        Produce values of self


        This is a hack to free subclasses from the requirement of self
        being an nd_array

        Parameters
        ----------
        None

        Returns
        -------
        v : array_like
        '''
        return self
def make_prob(x):
    x = np.array(x)
    return Prob(x.shape, buffer=x.data)

class Discrete_Observations:
    '''The simplest observation model: A finite set of integers.

    More complex observation models should provide the methods:
    *calc*, *random_out*, *reestimate* necessary for the application.

    Parameters
    ----------
    P_YS : array_like
        Conditional probabilites P_YS[s,y]

    '''
    def __init__(self,P_YS):
        self.P_YS = make_prob(P_YS)
        self.cum_y = np.cumsum(self.P_YS, axis=1)
        self.P_Y = None
        return
    def __str__(self):
        return 'P_YS =\n%s'%(self.P_YS,)
    def random_out(self,s):
        ''' For simulation, draw a random observation given state s

        Parameters
        ----------
        s : int
            Index of state

        Returns
        -------
        y : float
            Random observation drawn from distribution conditioned on state s
        '''
        return cum_rand(self.cum_y[s])
    def calc(self,y):
        """
        Calculate and return likelihoods: self.P_Y[t,i] = P(y(t)|s(t)=i)

        Parameters
        ----------
        y : array_like
            A sequence of integer observations

        Returns
        -------
        P_Y : array_like, floats
        """
        n_y = len(y)
        n_states = len(self.P_YS)
        self.P_Y = initialize(self.P_Y, (n_y, n_states))
        self.P_Y[:, :] = self.P_YS.likelihoods(y)
        return self.P_Y
    def reestimate(self,w,y):
        """
        Estimate new model parameters

        Parameters
        ----------
        w : array
            w[t,s] = Prob(state[t]=s) given data and old model
        y : array
            A sequence of integer observations

        Returns
        -------
        None
        """
        n_y = len(y)
        if not type(y) == np.ndarray:
            y = np.array(y, np.int32)
        assert(y.dtype == np.int32 and y.shape == (n_y,))
        for yi in range(self.P_YS.shape[1]):
            self.P_YS.assign_col(
                yi, w.take(np.where(y==yi)[0], axis=0).sum(axis=0))
        self.P_YS.normalize()
        self.cum_y = np.cumsum(self.P_YS, axis=1)
        return
class HMM:
    """A Hidden Markov Model implementation.

    Parameters
    ----------
    P_S0 : array_like
        Initial distribution of states
    P_S0_ergodic : array_like
        Stationary distribution of states
    P_SS : array_like
        P_SS[a,b] = Prob(s(1)=b|s(0)=a)
    P_YS : array_like
        P_YS[a,b] = Prob(y(0)=b|s(0)=a)
    prob=make_prob : function, optional
        Function to make conditional probability matrix

    Examples
    --------
    Illustrate/Test some methods by manipulating the HMM in Figure 1.6
    of the book.

    >>> P_S0 = np.array([1./3., 1./3., 1./3.])
    >>> P_S0_ergodic = np.array([1./7., 4./7., 2./7.])
    >>> P_SS = np.array([
    ...         [0,   1,   0],
    ...         [0,  .5,  .5],
    ...         [.5, .5,   0]
    ...         ],np.float64)
    >>> P_YS = np.array([
    ...         [1, 0,     0],
    ...         [0, 1./3., 2./3.],
    ...         [0, 2./3., 1./3.]
    ...         ])
    >>> mod = HMM(P_S0,P_S0_ergodic,P_YS,P_SS)
    >>> S,Y = mod.simulate(500)
    >>> Y = np.array(Y,np.int32)
    >>> E = mod.decode(Y)
    >>> table = ['%3s, %3s, %3s'%('y','S','Decoded')]
    >>> table += ['%3d, %3d, %3d'%triple for triple in zip(Y,S,E[:10])]
    >>> for triple in table:
    ...     print(triple)
      y,   S, Decoded
      2,   1,   1
      2,   1,   1
      1,   2,   2
      0,   0,   0
      1,   1,   1
      1,   2,   2
      2,   1,   1
      1,   2,   2
      2,   1,   1
      2,   2,   1
    >>> L = mod.train(Y,n_iter=4)
    it= 0 LLps=  -0.920
    it= 1 LLps=  -0.918
    it= 2 LLps=  -0.918
    it= 3 LLps=  -0.917
    >>> print(mod)
    <class '__main__.HMM'> with 3 states
    P_S0         = [ 0.     0.963  0.037]
    P_S0_ergodic = [ 0.142  0.58   0.278]
    P_SS =
    [[ 0.     1.     0.   ]
     [ 0.     0.519  0.481]
     [ 0.512  0.488  0.   ]]
    P_YS =
    [[ 1.     0.     0.   ]
     [ 0.     0.335  0.665]
     [ 0.     0.726  0.274]
    
    """
    def __init__(
        self,         # HMM instance
        P_S0,         # Initial distribution of states
        P_S0_ergodic, # Stationary distribution of states
        P_YS,         # P_YS[a,b] = Prob(y(0)=b|s(0)=a)
        P_SS,         # P_SS[a,b] = Prob(s(1)=b|s(0)=a)
        y_mod=Discrete_Observations,
        prob=make_prob# Function to make conditional probability matrix
        ):
        """Builds a new Hidden Markov Model
        """
        self.n_states = len(P_S0)
        self.P_S0 = np.array(P_S0)
        self.P_S0_ergodic = np.array(P_S0_ergodic)
        self.P_SS = prob(P_SS)
        self.y_mod = y_mod(P_YS)
        self.alpha = None
        self.gamma = None
        self.beta = None
        self.n_y = None
        return # End of __init__()
    def forward(self):
        """
        Implements recursive calculation of state probabilities given
        observation probabilities.

        Parameters
        ----------
        None

        Returns
        -------
        L : float
            Average log (base e) likelihood per point of entire observation
            sequence 

        Bullet points
        -------------

        On entry:

        * self          is an HMM

        * self.P_Y      has been calculated

        * self.n_y      is length of Y

        * self.n_states is number of states

        Bullet points
        -------------

        On return:

        * self.gamma[t] = Pr{y(t)=y(t)|y_0^{t-1}}
        * self.alpha[t,i] = Pr{s(t)=i|y_0^t}
        * return value is log likelihood of all data

        """

        # Ensure allocation and size of alpha and gamma
        self.alpha = initialize(self.alpha, (self.n_y, self.n_states))
        self.gamma = initialize(self.gamma, (self.n_y,))
        last = np.copy(self.P_S0.reshape(-1)) # Copy
        for t in range(self.n_y):
            last *= self.P_Y[t]              # Element-wise multiply
            self.gamma[t] = last.sum()
            last /= self.gamma[t]
            self.alpha[t, :] = last
            self.P_SS.step_forward(last)
        return (np.log(self.gamma)).sum() # End of forward()
    def backward(self):
        """
        Implements the Baum Welch backwards pass through state conditional
        likelihoods of the obserations.

        Parameters
        ----------
        None

        Returns
        -------
        None
        
        Bullet points
        -------------

        On entry:

        * self     is an HMM

        * self.P_Y has been calculated

        Bullet points
        -------------

        On return:

        * for each state i, beta[t,i] = Pr{y_{t+1}^T|s(t)=i}/Pr{y_{t+1}^T}

        """
        # Ensure allocation and size of beta
        self.beta = initialize(self.beta, (self.n_y, self.n_states))
        last = np.ones(self.n_states)
        # iterate
        for t in range(self.n_y-1, -1, -1):
            self.beta[t, :] = last
            last *= self.P_Y[t]
            last /= self.gamma[t]
            self.P_SS.step_back(last)
        return # End of backward()
    def train(self, y, n_iter=1, display=True):
        '''Based on observations y, do n_iter iterations of model reestimation

        Use Baum-Welch algorithm to search for maximum likelihood
        model parameters.

        Parameters
        ----------
        y : array_like
            Sequence of integer observations
        n_iter : int, optional
            Number of iterations
        display : bool, optional
            If True, print the log likelihood per observation for each
            iteration

        Returns
        -------
        LLL : list
            List of log likelihood per observation for each iteration

        '''
        # Do (n_iter) BaumWelch iterations
        LLL = []
        for it in range(n_iter):
            self.P_Y = self.y_mod.calc(y)
            self.n_y = len(self.P_Y)
            LLps = self.forward()/len(y) # log likelihood per step
            if display:
                print("it= %d LLps= %7.3f"%(it, LLps))
            LLL.append(LLps)
            self.backward()
            self.reestimate(y)
        return LLL # End of train()
    def reestimate_s(self):
        """Reestimate state transition probabilities and initial
        state probabilities.

        Given the observation probabilities, ie, self.state[s].P_Y[t],
        given alpha, beta, gamma, and P_Y, these calcuations are
        independent of the observation model calculations.

        Parameters
        ----------
        None

        Returns
        -------
        alpha*beta : array_like
            State probabilities give all observations

        """
        u_sum = np.zeros((self.n_states, self.n_states), np.float64)
        for t in np.where(self.gamma[1:]>0)[0]: # Skip segment boundaries
            u_sum += np.outer(self.alpha[t]/self.gamma[t+1],
                              self.P_Y[t+1]*self.beta[t+1, :])
        self.alpha *= self.beta
        wsum = self.alpha.sum(axis=0)
        self.P_S0_ergodic = np.copy(wsum)
        self.P_S0 = np.copy(self.alpha[0])
        for x in (self.P_S0_ergodic, self.P_S0):
            x /= x.sum()
        assert u_sum.shape == self.P_SS.shape
        self.P_SS.inplace_elementwise_multiply(u_sum)
        self.P_SS.normalize()
        return self.alpha # End of reestimate_s()
    def reestimate(self, y):
        """Reestimate all model paramters. In particular, reestimate
        observation model.

        Parameters
        ----------
        y : array
           Time series of observations

        Returns
        -------
        None

        """
        w = self.reestimate_s()
        self.y_mod.reestimate(w,y)
        return # End of reestimate()
    def decode(self, y):
        """Use the Viterbi algorithm to find the most likely state
           sequence for a given observation sequence y

        Parameters
        ----------
        y : array_like
            Sequence of observations

        Returns
        -------
        ss : array_like
            Maximum likelihood state sequence
        """
        self.P_Y = self.y_mod.calc(y)
        self.n_y = len(self.P_Y)
        pred = np.zeros((self.n_y, self.n_states), np.int32) # Best predecessors
        ss = np.zeros((self.n_y, 1), np.int32)        # State sequence
        L_s0, L_scs, L_p_y = (np.log(np.maximum(x, 1e-30)) for x in
                             (self.P_S0, self.P_SS.values(), self.P_Y))
        nu = L_p_y[0] + L_s0
        for t in range(1, self.n_y):
            omega = L_scs.T + nu
            pred[t, :] = omega.T.argmax(axis=0)   # Best predecessor
            nu = pred[t, :].choose(omega.T) + L_p_y[t]
        last_s = np.argmax(nu)
        for t in range(self.n_y-1, -1, -1):
            ss[t] = last_s
            last_s = pred[t,last_s]
        return ss.flat # End of viterbi
    # End of decode()
    def simulate(self, length, seed=3):
        """generates a random sequence of observations of given length

        Parameters
        ----------

        length : int
            Number of time steps to simulate
        seed : int, optional
            Seed for random number generator

        Returns
        -------

        states : array_like
            Sequence of states
        outs : array_like
            Sequence of observations
        """
        random.seed(seed)
        # Set up cumulative distributions
        cum_init = np.cumsum(self.P_S0_ergodic[0])
        cum_tran = np.cumsum(self.P_SS.values(), axis=1)
        # Initialize lists
        outs = []
        states = []
        # Select initial state
        i = cum_rand(cum_init)
        # Select subsequent states and call model to generate observations
        for t in range(length):
            states.append(i)
            outs.append(self.y_mod.random_out(i))
            i = cum_rand(cum_tran[i])
        return (states, outs) # End of simulate()
    def link(self, from_, to_, p):
        """ Create (or remove) a link between state "from_" and state "to_".

        The strength of the link is a function of both the argument
        "p" and the existing P_SS array.  Set P_SS itself if you
        need to set exact values.  Use this method to modify topology
        before training.

        Parameters
        ----------
        from_ : int
        to_ : int
        p : float

        Returns
        -------
        None

        FixMe: No test coverage.  Broken for cython code
        """
        self.P_SS[from_,to_] = p
        self.P_SS[from_, :] /= self.P_SS[from_, :].sum()
    def __str__(self):
        np.set_printoptions(precision=3)
        rv = '''
%s with %d states
P_S0         = %s
P_S0_ergodic = %s
P_SS =
%s
%s''' % (self.__class__, self.n_states, self.P_S0, self.P_S0_ergodic,
         self.P_SS.values(), self.y_mod
         )
        np.set_printoptions(precision=8)
        return rv[1:-1]
    def join_ys(
            self,    # HMM instance
            ys       # List of observation sequences
        ):
        """Concatenate and return multiple y sequences.  Also return
        information on sequence boundaries within concatenated list.

        Parameters
        ----------
        ys : list
            A list of observation sequences.  Default int, but must match
            method self.P_Y() if subclassed

        Returns
        -------
        n_seg : int
            Number of component segments
        t_seg : list
            List of ints specifying endpoints of segments within y_all
        y_all : list
            Concatenated list of observations

        """
        t_seg = [0] # List of segment boundaries in concatenated ys
        y_all = []
        for seg in ys:
            y_all += list(seg)
            t_seg.append(len(y_all))
        self.n_y = t_seg[-1]
        return len(t_seg)-1, t_seg, y_all
    def multi_train(
            self,         # HMM instance
            ys,           # List of observation sequences
            n_iter=1,
            boost_w=None, # Optional weight of each observation for reestimation
            display=True
        ):
        '''Train on multiple sequences of observations

        Parameters
        ----------
        ys : list
            list of sequences of integer observations
        n_iter : int, optional
            Number of iterations
        boost_w : array_like, optional
            Weight of each observation for reestimation
        display : bool, optional
            If True, print the log likelihood per observation for each
            segment and each iteration

        Returns
        -------
        avgs : list
            List of log likelihood per observation for each iteration

        Examples
        --------
        Same model as used to demonstrate train().  Here simulated
        data is broken into three independent segments for training.
        For each iteration, "L[i]" gives the log likelihood per data
        point of segment "i".  Note that L[2] does not improve
        monotonically but that the average over segments does.

        >>> P_S0 = np.array([1./3., 1./3., 1./3.])
        >>> P_S0_ergodic = np.array([1./7., 4./7., 2./7.])
        >>> P_SS = np.array([
        ...         [0,   1,   0],
        ...         [0,  .5,  .5],
        ...         [.5, .5,   0]
        ...         ],np.float64)
        >>> P_YS = np.array([
        ...         [1, 0,     0],
        ...         [0, 1./3., 2./3.],
        ...         [0, 2./3., 1./3.]
        ...         ])
        >>> mod = HMM(P_S0,P_S0_ergodic,P_YS,P_SS)
        >>> S,Y = mod.simulate(600)
        >>> ys = []
        >>> for i in [1,2,0]:
        ...     ys.append(list(Y[200*i:200*(i+1)]))
        >>> A = mod.multi_train(ys,3)
        i=0: L[0]=-0.9162 L[1]=-0.9142 L[2]=-0.9275 avg=-0.9193117
        i=1: L[0]=-0.9156 L[1]=-0.9137 L[2]=-0.9278 avg=-0.9190510
        i=2: L[0]=-0.9153 L[1]=-0.9135 L[2]=-0.9280 avg=-0.9189398

        '''
        n_seg, t_seg, y_all = self.join_ys(ys)
        avgs = n_iter*[None] # Average log likelihood per step
        t_total = t_seg[-1]
        alpha_all = initialize(self.alpha, (t_total, self.n_states))
        beta_all = initialize(self.beta, (t_total, self.n_states))
        gamma_all = initialize(self.gamma, (t_total,))
        P_S0_all = np.empty((n_seg, self.n_states))
        #P_S0_all are state probabilities at the beginning of each segment
        for seg in range(n_seg):
            P_S0_all[seg, :] = self.P_S0.copy()
        for i in range(n_iter):
            if display:
                print('i=%d: '%i, end='')
            tot = 0.0
            # Both forward() and backward() should operate on each
            # training segment and put the results in the
            # corresponding segement of the the alpha, beta and gamma
            # arrays.
            P_Y_all = self.y_mod.calc(y_all)
            for seg in range(n_seg):
                self.n_y = t_seg[seg+1] - t_seg[seg]
                self.alpha = alpha_all[t_seg[seg]:t_seg[seg+1], :]
                self.beta = beta_all[t_seg[seg]:t_seg[seg+1], :]
                self.P_Y = P_Y_all[t_seg[seg]:t_seg[seg+1]]
                self.gamma = gamma_all[t_seg[seg]:t_seg[seg+1]]
                self.P_S0 = P_S0_all[seg, :]
                LL = self.forward() #Log Likelihood
                if display:
                    print('L[%d]=%7.4f '%(seg,LL/self.n_y), end='')
                tot += LL
                self.backward()
                self.P_S0 = self.alpha[0] * self.beta[0]
                self.gamma[0] = -1 # Don't fit transitions between segments
            avgs[i] = tot/t_total
            if i>0 and avgs[i-1] >= avgs[i]:
                print('''
WARNING training is not monotonic: avg[%d]=%f and avg[%d]=%f
'''%(i-1,avgs[i-1],i,avgs[i]))
            if display:
                print('avg=%10.7f'% avgs[i])
            # Associate all of the alpha and beta segments with the
            # states and reestimate()
            self.alpha = alpha_all
            self.beta = beta_all
            self.gamma = gamma_all
            self.P_Y = P_Y_all
            if boost_w != None:
                self.alpha *= BoostW
            self.n_y = len(y_all)
            self.reestimate(y_all)
        self.P_S0[:] = P_S0_all.sum(axis=0)
        self.P_S0 /= self.P_S0.sum()
        return avgs
class HMMc(HMM):
    '''Models that permit each state to be a member of
    a class_ (not the python reserved word).

    '''
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

#--------------------------------
# Local Variables:
# mode: python
# End:
