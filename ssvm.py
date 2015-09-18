from cvxopt import matrix,spmatrix,sparse,normal,spdiag
from cvxopt.blas import dot,dotu
from cvxopt.solvers import qp
import numpy as np
import math as math

class SSVM(object):
    """ (Primal) Structured Output Support Vector Machine
        Written by Nico Goernitz, TU Berlin, 2014
    """

    C = 1.0  # (scalar) the regularization constant > 0
    sobj = []  # structured object contains various functions
               # e.g. get_num_dims(), get_num_samples(), get_sample(i), argmax(sol,i)
               # should be inherited by so_interface
    w = []  # (vector) solution vector
    slacks = []  # (vector) slack variables

    def __init__(self, sobj, C=1.0):
        self.C = C
        self.sobj = sobj

    def train(self, heur_constr=10.4, max_iter=100):
        N = self.sobj.get_num_samples()
        DIMS = self.sobj.get_num_dims()

        w = self.sobj.get_hotstart()

        slacks = matrix(0.0, (1,N))
        sol = matrix([[w.trans()],[slacks]]).trans()

        # quadratic regularizer
        P = spdiag(matrix([[matrix(0.0,(1,N))],[matrix(1.0,(1,DIMS))]]))
        q = self.C*matrix([matrix(1.0,(N,1)),matrix(0.0,(DIMS,1))])

        # inequality constraints inits Gx <= h
        G1 = spdiag(matrix([[matrix(-1.0,(1,N))],[matrix(0.0,(1,DIMS))]]))
        G1 = G1[0:N,:]
        h1 = matrix(0.0,(1,N))

        dpsi = matrix(0.0,(DIMS,0))
        delta = matrix(0.0,(1,0))
        trigger = matrix(0.0,(N,0))

        iter = 0
        newConstr = N
        while (newConstr>0 and iter<max_iter):

            newConstr=0
            for i in range(N):
                self.sobj.update_solution(w)
                (val, ypred, psi_i) = self.sobj.map(i, add_loss=True)
                psi_true = self.sobj.get_joint_feature_map(i)

                v_true = w.trans()*psi_true
                v_pred = w.trans()*psi_i
                loss = self.sobj.get_loss(i,ypred)

                if (slacks[i] < np.single(loss-v_true+v_pred)):
                    dpsi = matrix([[dpsi],[-(psi_true-psi_i)]])
                    delta = matrix([[delta],[-loss]])
                    tval = matrix(0.0,(N,1))
                    tval[i] = -1.0
                    trigger = sparse([[trigger],[tval]])
                    newConstr += 1

            # G1/h1: -\xi_i <= 0
            # G2/h2: -dpsi -xi_i <= -delta_i
            G2 = sparse([[trigger.trans()],[dpsi.trans()]])
            h2 = delta

            # skip fullfilled constraints for this run (heuristic)
            if (iter>2):
                diffs = np.array(delta - (G2*sol).trans())
                inds = np.where(diffs<heur_constr)[1]
                inds = list([int(inds[i]) for i in range(len(inds))])
                G2 = G2[inds, :]
                h2 = delta[:, inds]
                print('Iter{0}: Solving with {1} of {2} constraints.'.format(iter,len(inds),diffs.shape[1]))

            # Solve the intermediate QP using cvxopt
            G = sparse([G1, G2])
            h = matrix([[h1], [h2]])
            res = qp(P, q, G, h.trans())

            obj_primal = res['primal objective']
            sol = res['x']
            slacks = sol[0:N]
            w = sol[N:N+DIMS]
            print('Iter{0}: objective {1} #new constraints {2}'.format(iter,obj_primal,newConstr))
            iter += 1

        # store obtained solution
        self.w = w
        self.slacks = slacks
        return w, slacks

    def apply(self, pred_sobj):
        """ Application of the SSVM:
                value = max_y <w,\Psi(x,y)>
                struct = argmanx_y <w,\Psi(x,y)>
        """
        N = pred_sobj.get_num_samples()
        vals = []
        structs = []
        for i in range(N):
            pred_sobj.update_solution(self.w)
            (val, struct, foo) = pred_sobj.map(i, add_loss=False)
            vals.append(val)
            structs.append(struct)
        return vals, structs
