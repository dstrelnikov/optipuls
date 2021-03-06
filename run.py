import argparse

import dolfin
from dolfin import Constant
import numpy as np

import optipuls.visualization as vis
from optipuls.simulation import Simulation
from optipuls.problem import Problem
from optipuls.mesh import mesh, R, R_laser, Z
import optipuls.coefficients as coefficients
import optipuls.optimization as optimization
from optipuls.time import TimeDomain


# parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', default='../output')
parser.add_argument('-s', '--scratch', default='/scratch/OptiPuls/current')
args = parser.parse_args()


# set dolfin parameters
dolfin.set_log_level(40)
dolfin.parameters["form_compiler"]["quadrature_degree"] = 1



P_YAG = 2000.
absorb = 0.135
R_laser = 0.0002
laser_pd = (absorb * P_YAG) / (np.pi * R_laser**2)

# set up the problem
problem = Problem()

time_domain = TimeDomain(0.015, 30)
problem.time_domain = time_domain

problem.P_YAG = P_YAG
problem.laser_pd = laser_pd

problem.temp_amb = 295.
problem.implicitness = 1.
problem.convection_coeff = 20.
problem.radiation_coeff = 2.26 * 10**-9
problem.liquidus = 923.0
problem.solidus = 858.0

# optimization parameters
problem.control_ref = np.zeros(time_domain.Nt)
problem.beta_control = 10**2
problem.beta_velocity = 10**18
problem.velocity_max = 0.15
problem.beta_liquidity = 10**12
problem.beta_welding = 10**-2
problem.threshold_temp = 1000.
problem.target_point = dolfin.Point(0, .7*Z)
problem.pow_ = 20

# initialize FEM spaces
problem.V = dolfin.FunctionSpace(mesh, "CG", 1)
problem.V1 = dolfin.FunctionSpace(mesh, "DG", 0)

problem.theta_init = dolfin.project(problem.temp_amb, problem.V)


coefficients.vhc.problem = problem
coefficients.kappa_rad.problem = problem
coefficients.kappa_ax.problem = problem

problem.vhc = coefficients.vhc
problem.kappa = coefficients.kappa


print('Creating a test simulation.')
test_control = 0.5 + 0.1 * np.sin(0.5 * time_domain.timeline / np.pi)
test_simulation = Simulation(problem, test_control)

epsilons, deltas_fwd = optimization.gradient_test(
        test_simulation, eps_init=10**-5, iter_max=15)
vis.gradient_test_plot(
        epsilons, deltas_fwd, outfile=args.scratch+'/gradient_test.png')
print(f'Gradient test complete. See {args.scratch}/gradient_test.png')

print('Creating an initial simulation.')
control = np.zeros(time_domain.Nt)
simulation = Simulation(problem, control)

descent = optimization.gradient_descent(
        simulation, iter_max=100, step_init=2**-25)

vis.control_plot(
        descent[-1].control,
        labels=['Optimal Control'],
        outfile=args.scratch+'/optimal_control.png')
print(f'Gradient descent complete. See {args.scratch}/optimal_control.png')
