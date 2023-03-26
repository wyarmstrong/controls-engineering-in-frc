#!/usr/bin/env python3

"""Simulates drivetrain velocity control with a time delay."""

import sys

import frccontrol as fct
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import scipy as sp

from bookutil import latex

if "--noninteractive" in sys.argv:
    mpl.use("svg")
plt.rc("text", usetex=True)


class Drivetrain:
    """An frccontrol system representing a drivetrain with a time delay."""

    def __init__(self, dt, delay=0.0):
        """Drivetrain subsystem.

        Keyword arguments:
        dt -- time between model/controller updates
        delay -- input delay in seconds
        """
        self.dt = dt
        self.delay = delay

        Kv = 3.02
        Ka = 0.642

        A = np.array([[-Kv / Ka]])
        B = np.array([[1.0 / Ka]])
        C = np.array([[1]])
        D = np.array([[0]])

        self.plant = sp.signal.StateSpace(A, B, C, D)

        # Sim variables
        self.sim = self.plant.to_discrete(self.dt)
        self.x = np.zeros((1, 1))
        self.u = np.zeros((1, 1))
        self.y = np.zeros((1, 1))

        # States: angular velocity (rad/s)
        # Inputs: voltage (V)
        # Outputs: angular velocity (rad/s)
        self.feedforward = fct.LinearPlantInversionFeedforward(
            self.plant.A, self.plant.B, self.dt
        )
        self.feedback = fct.LinearQuadraticRegulator(
            self.plant.A, self.plant.B, [0.2], [7.0], self.dt
        )

        # Prepare time delay
        self.ubuf = []
        for _ in range(int(self.delay / self.dt)):
            self.ubuf.append(np.zeros((1, 1)))

        self.u_min = np.array([[-12.0]])
        self.u_max = np.array([[12.0]])

    def update(self, r, next_r):
        """
        Advance the model by one timestep.

        Keyword arguments:
        r -- the current reference
        next_r -- the next reference
        """
        # Update sim model
        self.x = self.sim.A @ self.x + self.sim.B @ self.u
        self.y = self.sim.C @ self.x + self.sim.D @ self.u

        self.u = np.clip(
            self.feedforward.calculate(next_r) + self.feedback.calculate(self.x, r),
            self.u_min,
            self.u_max,
        )
        self.ubuf.append(self.u)
        self.u = self.ubuf.pop(0)


class PlotMetadata:
    """
    Plot metadata.
    """

    def __init__(self, delay, compensate, gain_digits, plot_filename):
        """
        Constructs PlotMetadata.

        Keyword arguments:
        delay -- the input delay
        compensate -- whether to perform latency compensation
        gain_digits -- number of digits to include in feedback gain plot label
        plot_filename -- plot filename
        """
        self.delay = delay
        self.compensate = compensate
        self.gain_digits = gain_digits
        self.plot_filename = plot_filename


def main():
    """Entry point."""

    dt = 0.001

    # Set up graphing
    l0 = 0.1
    l1 = l0 + 5.0
    l2 = l1 + 0.1
    ts = np.arange(0, l2 + 5.0, dt)

    # Generate references
    refs = []
    for t in ts:
        if t < l0:
            r = np.array([[0.0]])
        elif t < l1:
            r = np.array([[2.0]])
        else:
            r = np.array([[0.0]])
        refs.append(r)

    # Run simulations
    for plot in [
        PlotMetadata(0.04, False, 2, "drivetrain_time_delay_no_comp"),
        PlotMetadata(0.04, True, 2, "drivetrain_time_delay_comp"),
    ]:
        drivetrain = Drivetrain(dt, plot.delay)
        if plot.compensate:
            drivetrain.feedback.latency_compensate(
                drivetrain.plant.A, drivetrain.plant.B, drivetrain.dt, plot.delay
            )

        x_rec, r_rec, u_rec, _ = fct.generate_time_responses(drivetrain, refs)

        plt.figure()

        # Plot velocity
        plt.subplot(2, 1, 1)
        plt.ylabel("Velocity (m/s)")
        plt.plot(
            ts,
            x_rec[0, :],
            label=f"State ($K_p = {round(drivetrain.feedback.K[0, 0], plot.gain_digits)}$)",
        )
        plt.plot(ts, r_rec[0, :], label="Reference")
        plt.legend()

        # Plot voltage
        plt.subplot(2, 1, 2)
        plt.ylabel("Voltage (V)")
        plt.plot(ts, u_rec[0, :], label="Input")
        plt.legend()
        plt.xlabel("Time (s)")

        if "--noninteractive" in sys.argv:
            latex.savefig(plot.plot_filename)

    if "--noninteractive" not in sys.argv:
        plt.show()


if __name__ == "__main__":
    main()
