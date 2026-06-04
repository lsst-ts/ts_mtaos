.. _Closed_Loop_Analysis:

##########################################
Closed Loop Behavior Analysis
##########################################

This section presents an analysis of the MTAOS closed-loop behavior, focusing on the parameter space, special cases that modify control parameters at runtime,
and potential issues identified during code review.

This analysis was motivated by the question: 
*"What is the current logic and parameter space options, including all the special cases that trigger changes in the parameters of the state estimation and PID loop?"*

For the factual description of the closed loop flow and its configuration, see :ref:`Closed_Loop_Operations`.

.. _Closed_Loop_Comparison:

Comparison: Closed Loop vs close_loop Script
============================================

Both paths use the same PID controller
----------------------------------------

Both the ``close_loop_lsstcam.py`` script and the MTAOS :py:meth:`~lsst.ts.mtaos.MTAOS.run_closed_loop` task call the **same underlying OFC** (``ts_ofc``) through the same MTAOS commands.
The script calls ``cmd_runOFC`` which internally invokes :py:meth:`~lsst.ts.mtaos.MTAOS._execute_ofc` — the same function the closed loop calls directly.

In both cases, the per-iteration correction is computed by:

1. State estimation (``dof_state`` from wavefront error)
2. PID ``control_step``: ``uk = kp × error + ki × integral + kd × derivative``
3. DOF aggregation and component corrections

The PID integral is reset in both paths (due to ``comp_dof_idx`` set/restore triggering ``reset_history()``), so both effectively operate as proportional-only controllers.

Outer loop orchestration differs
---------------------------------

The difference is in **how the outer loop is managed** — who decides when to take images, what gain to use, and when to stop:

**close_loop script:**

.. code-block:: text

   for i in range(max_iter):
       1. Point telescope (fixed az/el/rot)
       2. Take image (script controls timing)
       3. cmd_runWEP → MTAOS processes WFE
       4. cmd_runOFC(userGain=gain_sequence[i]) → MTAOS runs PID
       5. cmd_issueCorrection → apply
       6. Check: if visitDoF < threshold → STOP
   If max_iter reached → stop with warning

**MTAOS closed loop:**

.. code-block:: text

   while enabled:
       1. Wait for OODS image event (scheduler controls pointing)
       2. Filter image (stale? pointing changed?)
       3. _execute_wavefront_estimation → WEP
       4. Compute gain from elevation delta
       5. _execute_ofc(userGain=gain) → PID
       6. Wait shutter closed → apply correction
       7. No convergence check → continue waiting

Summary table
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 37 38

   * - Aspect
     - close_loop script
     - MTAOS closed loop
   * - Control algorithm
     - Same PID (via ``cmd_runOFC``)
     - Same PID (via ``_execute_ofc``)
   * - Image source
     - Script takes images (synchronous)
     - Reacts to OODS events (asynchronous)
   * - Pointing
     - Fixed az/el/rot (re-pointed each iteration)
     - Variable (FBS scheduler decides)
   * - Gain source
     - ``gain_sequence`` (scalar per iteration, e.g. [0.75, 0.75, 0.5])
     - ``controller.kp`` array, scaled by elevation delta
   * - Outer loop termination
     - Stops when ``visitDoF < threshold`` or ``max_iter`` reached
     - No termination condition; runs until ``stopClosedLoop``
   * - Elevation scaling
     - None (fixed pointing)
     - Yes (skip/scale based on consecutive image elevations)
   * - Stale image handling
     - N/A (script takes fresh images immediately)
     - ``discard_intermediate_corrections``
   * - PID integral
     - Reset each iteration (same ``comp_dof_idx`` mechanism)
     - Reset each iteration (same mechanism)

How the script achieves convergence
------------------------------------

The script converges **not** through PID integral buildup, but through repeated proportional corrections:

1. Each iteration measures the **current** optical state (fresh image)
2. The PID computes ``uk = kp × state`` (proportional-only, since integral is reset)
3. The correction reduces the state by the ``kp`` fraction
4. The next iteration measures the reduced state
5. If the remaining state is below ``threshold``, stop

With ``kp = 0.75``:

- Iteration 1: correct 75% → 25% remains
- Iteration 2: correct 75% of 25% → 6.25% remains
- Iteration 3: correct 75% of 6.25% → 1.56% remains

This geometric convergence works because the telescope is at a **fixed pointing** — the optical state doesn't change between iterations except for the correction applied.

Why the MTAOS closed loop does not converge the same way
---------------------------------------------------------

The MTAOS closed loop cannot converge in the same sense because:

- The telescope **slews between images** — the optical state changes due to gravity, thermal effects, and LUT residuals at each new pointing
- The "target" (zero DOF state) is never reached because the real optical state keeps changing with each new field
- The gain (kp=0.45) is lower than the script's typical gain (0.5–0.75)
- Each correction addresses the state at the *previous* pointing, not the current one

The closed loop is designed to **track** a changing optical state, not converge to a fixed point.
The question is whether the current orchestration (gain values, timing, position checks) achieves good tracking.

.. _Closed_Loop_Key_Behaviors:

Key Behaviors
=============

The following behaviors emerge from the current implementation and configuration.

Proportional-only control
--------------------------

The ``comp_dof_idx`` set/restore cycle in :py:meth:`~lsst.ts.mtaos.MTAOS._execute_ofc` resets the PID integral, derivative, and previous error every iteration.
Combined with the current config (``ki=0``, ``kd=0``), the controller operates as proportional-only.
Even if ``ki`` or ``kd`` were configured non-zero, they would not accumulate across iterations.

Implication: the system cannot build up correction for persistent biases that the proportional term alone cannot eliminate in a single step.
Whether this matters depends on how well the subsystem LUTs pre-compensate for gravity and thermal effects.

``zn_selected`` is overridden by WEP
--------------------------------------

The ``zn_selected`` parameter from configuration is overwritten inside :py:meth:`~lsst.ts.mtaos.Model.calculate_corrections` (line 1683) by the Zernike indices that WEP actually produced.
The configured value has no effect on the final correction.

Two elevation checks with different semantics
----------------------------------------------

Elevation is checked at two separate points:

1. **Image filtering** (before WEP):
   compares the image's position to the *live telescope position*.
   Also checks rotation.
   Purpose: skip images from a position the telescope has already left.

2. **Gain scaling** (after WEP, before OFC):
   compares *consecutive image elevations* (previous vs current).
   Purpose: detect large slews between observations and reduce gain.
   Does not check rotation.

These are distinct checks with different reference points and different actions (skip vs scale).

Configuration precedence
-------------------------

Parameters are loaded at three levels:

1. **OFC controller config** (``MTAOS/ofc/configurations/init.yaml``)
   — loaded at OFCData initialization.
2. **CSC config** (``MTAOS/v13/_init.yaml``)
   — applied at CSC startup; overrides OFC-level.
3. **Runtime config** (:py:meth:`~lsst.ts.mtaos.MTAOS.do_startClosedLoop`)
   — applied per iteration; overrides both previous levels.

WEP output overrides ``zn_selected`` regardless of all three levels.

.. _Closed_Loop_Identified_Issues:

Identified Issues
=================

The following items have been identified during code review.
They are documented here for future investigation and discussion.

No position re-check at correction application time
-----------------------------------------------------

The timeline of a single correction cycle:

.. code-block:: text

   T0: Image arrives (OODS event)
   T1: Image filtering — compare image position vs LIVE telescope position
       If delta > limit → skip (correct at this moment)
   T2: WEP runs (~5–30+ seconds, telescope slews to next field)
   T3: Gain scaling — compares consecutive image elevations
   T4: OFC computes correction (seconds)
   T5: Wait for camera shutter to close
   T6: Apply correction — NO position re-check

Between T1 and T6, typically 30+ seconds elapse.
During this time the scheduler may slew the telescope to a different field.
The check at T1 was valid *at that moment*, but by T6 the telescope may be at a significantly different elevation and rotator angle.

The correction computed from the image at T0's position is applied at T6's (potentially different) position.
Neither ``discard_intermediate_corrections`` nor the gain scaling check addresses this gap.

A potential improvement: re-read the live telescope position at T6 and skip or scale the correction if the delta between the image's position and the current position exceeds a threshold.

Filter change during processing
---------------------------------

The code detects filter changes by comparing filter metadata of consecutive processed images.
When detected, ``closed_loop_filter_change_gain`` can override gains for N subsequent iterations (currently disabled: ``n_iter = 0``).
The image that triggered the detection is still processed — not skipped.

DOF corrections are largely filter-independent, so applying a correction from a different filter may be valid.
However, if a filter change occurs *during* processing, the hexapod filter LUT applies filter-dependent z-offsets, changing the optical state under the correction.
This edge case is not currently handled.

PID integral reset
-------------------

The integral reset (due to ``comp_dof_idx`` set/restore) prevents the controller from accumulating correction for persistent biases.
If biases exist (imperfect LUTs, unmodeled thermal effects), the proportional term can only reduce them by the ``kp`` fraction per iteration — never reaching zero.

Whether this is a practical limitation depends on:

- Magnitude of persistent biases vs measurement noise
- Quality of subsystem LUT compensation
- Target image quality requirements

