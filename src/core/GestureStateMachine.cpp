#include "GestureStateMachine.h"

QString GestureStateMachine::filterGesture(const QString &hand,
                                           const QString &rawGesture)
{
    State &st = perHand_[hand];

    if (rawGesture == st.lastGesture)
    {
        st.framesStable++;
    }
    else
    {
        st.lastGesture = rawGesture;
        st.framesStable = 0;
    }

    // Require 3 stable frames for a change
    if (st.framesStable >= 3)
        st.stableGesture = rawGesture;

    return st.stableGesture;
}
