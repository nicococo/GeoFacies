import numpy as np
from cvxopt import matrix, mul

from structured_object import StructuredObject


class MulticlassRegressionModel(StructuredObject):
    """ (Transductive) Multi-class Regression Map.
        Number of latent classes must be set in advance.
        Target values 'y' are continuous regression targets.

        For use in transductive settings, 'trans_idx' contains
        the indices of elements in 'X' that do not have any
        regression targets.
    """
    num_classes = -1  # (scalar) number of classes
    trans_idx = None

    def __init__(self, X, classes, y=None, trans_idx=None):
        StructuredObject.__init__(self, X, y)
        self.num_classes = classes
        self.trans_idx = trans_idx
        if not trans_idx:
            self.trans_idx = list()

    def map(self, idx=-1, add_loss=False, add_prior=False, theta=0.5):
        # opt_type = 'quadratic':
        # the argmax is equal to the argmax of the linear function
        # foo = -normSol + 2*foo - normPsi
        # since ||\Psi(x_i,z)|| = ||\phi(x_i)|| = y \forall z
        # and normSol is also constant
        if isinstance(self.sol, list) and not idx in self.trans_idx:
            sol_v = self.sol[0]
            sol_u = self.sol[1]
            target = 0.0
            if self.y is not None:
                target = self.y[idx]

            v = matrix(np.array(sol_v).reshape((self.feats, self.num_classes), order='F'))
            f_density = v.trans()*self.X[:, idx]

            u = matrix(np.array(sol_u).reshape((self.feats, self.num_classes), order='F'))
            f_squares = target - u.trans()*self.X[:, idx]
            f_squares = mul(f_squares, f_squares)

            foo = (1.0-theta) * f_density - theta * f_squares
        else:
            v = matrix(np.array(self.sol).reshape((self.feats, self.num_classes), order='F'))
            f_density = v.trans()*self.X[:, idx]
            foo = (1.0-theta) * f_density

        # highest value first
        inds = np.argsort(-foo, axis=0)[0]
        cls = inds[0]
        val = foo[cls]

        psi_idx = self.get_joint_feature_map(idx, cls)
        return val, cls, psi_idx

    def get_joint_feature_map(self, idx, y=None):
        if y is None:
            y = self.y[idx]
        nd = self.feats
        mc = self.num_classes
        psi = matrix(0.0, (nd*mc, 1))
        psi[nd*y:nd*(y+1)] = self.X[:, idx]
        return psi

    def get_num_dims(self):
        return self.feats*self.num_classes

    def evaluate(self, pred):
        super(MulticlassRegressionModel, self).evaluate(pred)