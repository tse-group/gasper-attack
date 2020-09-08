#! /usr/bin/env python3.8


from __future__ import annotations
from dataclasses import dataclass, field
import random
import copy


@dataclass
class Scenario(object):
    C: int
    N: int
    F: int

    def __post_init__(self):
        assert (self.N % self.C) == 0

    def slot_to_epoch(self, slot):
        return (slot // self.C, slot % self.C)

    def committee_size(self):
        return self.N // self.C

    def is_adversarial(self, i):
        return i < self.F

    def is_honest(self, i):
        return not self.is_adversarial(i)

    def all_parties(self):
        return range(self.N)


@dataclass
class RandomSchedule(object):
    scenario: Scenario
    randomness: int

    def committee_for_slot(self, slot):
        (epoch, slot_within_block) = self.scenario.slot_to_epoch(slot)
        committee_size = self.scenario.committee_size()

        rnd = random.Random(self.randomness + epoch)
        committees = list(self.scenario.all_parties())
        rnd.shuffle(committees)

        return committees[(slot_within_block*committee_size):((slot_within_block+1)*committee_size)]

    def committee_fractions_for_slot(self, slot):
        committee = self.committee_for_slot(slot)
        return ({ i for i in committee if self.scenario.is_adversarial(i) }, { i for i in committee if self.scenario.is_honest(i) })

    def proposer_for_slot(self, slot):
        committee = self.committee_for_slot(slot)
        return committee[0]

    def role_assignment_for_attack(self):
        # slot 0 needs to have an adversarial proposer who will propose two competing blocks to subsets of the honest (or adversarial fillers) validators
        adv_proposer_slot0 = None
        # during epoch 0, `swayers' (with withheld votes) from slot (i-1) will be used to split honest validators of slot i
        adv_swayers_during_epoch0 = set()
        # during epoch 1 and beyond, `swayers' (with withheld votes) from the epoch before will be used to split honest validators
        adv_swayers_during_epoch1 = set()
        # during epoch 0 it is important that each slot have evenly many validators, so the adversary might `donate' one honest-pretending `filler'
        adv_fillers_during_epoch0 = set()

        # make sure the proposer in slot 0 is adversarial
        prop0 = self.proposer_for_slot(0)
        if not self.scenario.is_adversarial(prop0):
            print(" -> proposer in slot 0 is not adversarial")
            return (False, None)
        else:
            adv_proposer_slot0 = prop0

        # make sure enough adversarial parties exist per slot during epoch 0
        for slot in range(self.scenario.C):
            (c_adversarial, c_honest) = self.committee_fractions_for_slot(slot)
            if slot == 0:
                # the proposer of slot 0 should not be used for adversarial purposes anymore, as it is already equivocating
                c_adversarial -= {adv_proposer_slot0,}
            
            if len(c_honest) % 2 == 1:
                # we need to balance the honest vote to an even number of voters by filling in an adversarial voter (`filler')
                if len(c_adversarial) == 0:
                    print(f" -> insufficient adversarial vote in slot {slot} to fill up to even number of honest voters")
                    return (False, None)
                else:
                    adv_fillers_during_epoch0 |= {c_adversarial.pop(),}

            if slot < self.scenario.C - 1:
                # we need to recruit two adversarial votes to split honest voters in the next slot (`swayers')
                if len(c_adversarial) < 2:
                    print(f" -> insufficient adversarial vote in slot {slot} to split honest voters in next slot")
                    return (False, None)
                else:
                    adv_swayers_during_epoch0 |= {c_adversarial.pop(), c_adversarial.pop(),}

            # we need to recruit two adversarial votes to split honest voters in the next epoch by releasing votes very late (`swayers')
            # (these do not have to come two per slot, it could also be just all the `leftover adversaries',
            # as long as there are enough -- but this makes the simulation easier and doesn't seem to affect attack chances that much)
            if len(c_adversarial) < 2:
                print(f" -> insufficient adversarial vote in slot {slot} to split honest voters in next epoch")
                return (False, None)
            else:
                adv_swayers_during_epoch1 |= {c_adversarial.pop(), c_adversarial.pop(),}

        # ensure we recruited the right amount of adversarial parties for the required roles
        assert len(adv_swayers_during_epoch0) == 2 * (self.scenario.C - 1)
        assert len(adv_swayers_during_epoch1) == 2 * self.scenario.C
        assert len(adv_fillers_during_epoch0) < self.scenario.C

        return (True, (adv_proposer_slot0, adv_swayers_during_epoch0, adv_swayers_during_epoch1, adv_fillers_during_epoch0))

    def is_attack_feasible(self):
        (ret, roles) = self.role_assignment_for_attack()
        return ret


VOTED_N = 0   # never
VOTED_G = 1   # genesis
VOTED_L = 2   # left
VOTED_R = 3   # right

def balance(lmd):
    return (lmd.count(VOTED_L), lmd.count(VOTED_R))

def leading(lmd):
    if lmd.count(VOTED_L) > lmd.count(VOTED_R):
        return VOTED_L
    elif lmd.count(VOTED_L) < lmd.count(VOTED_R):
        return VOTED_R
    elif lmd.count(VOTED_L) == lmd.count(VOTED_R):
        return None
    else:
        assert False



# parameters of the scenario

# scenario = Scenario(20, 500, 161)
scenario = Scenario(64, 12800, 320*2)
NUM_SLOTS_SIMULATE = 100 * scenario.C


# find a random seed so that the adversary can pull off the attack in epoch 0
# (this tells us in how many epochs the adversary can pull off this attack -- quite a lot!)

rnd_tries = 0
while True:
    rnd_tries += 1
    print(rnd_tries, "try to find suitable epoch ...")
    schedule = RandomSchedule(scenario, 42 + rnd_tries)
    (attack_feasible, attack_roles) = schedule.role_assignment_for_attack()
    if attack_feasible:
        break

(adv_proposer_slot0, adv_swayers_during_epoch0, adv_swayers_during_epoch1, adv_fillers_during_epoch0) = attack_roles
print("adversarial proposer in slot 0:", adv_proposer_slot0)
print("swayers during epoch 0:", adv_swayers_during_epoch0)
print("swayers during epoch 1 (and beyond):", adv_swayers_during_epoch1)
print("fillers during epoch 0:", adv_fillers_during_epoch0)


# set up latest votes as seen globally
lmd = [ VOTED_N for i in scenario.all_parties() ]


# SLOT 0 (EPOCH 0)
# the adversarial proposer equivocates and puts out two blocks, starting two chains, (L)eft and (R)ight

# add filler (if any) for slot 0 to honest validators
(cm_adv, cm_hon) = schedule.committee_fractions_for_slot(0)
will_vote_honestly = cm_hon | (cm_adv & adv_fillers_during_epoch0)
N_will_vote_honestly = len(will_vote_honestly)

assert len(will_vote_honestly) % 2 == 0

# split into who will vote left/right (this is implemented by the adversarial proposer equivocating and sharing
# two different blocks with the respective subsets of validators)
force_vote_L = [ will_vote_honestly.pop() for i in range(N_will_vote_honestly // 2) ]
force_vote_R = [ will_vote_honestly.pop() for i in range(N_will_vote_honestly // 2) ]

assert len(will_vote_honestly) == 0

# votes left
for i in force_vote_L:
    lmd[i] = VOTED_L

# votes right
for i in force_vote_R:
    lmd[i] = VOTED_R

# check the balance
print(f"slot 0 balance:", balance(lmd))
assert not leading(lmd)


# SLOT 1 .. (C-1) (EPOCH 0):

for slot in range(1, scenario.C):
    (cm_adv_prev, cm_hon_prev) = schedule.committee_fractions_for_slot(slot - 1)
    (cm_adv_cur, cm_hon_cur) = schedule.committee_fractions_for_slot(slot)

    # add `filler' (if any) for slot i to honest validators
    will_vote_honestly = cm_hon_cur | (cm_adv_cur & adv_fillers_during_epoch0)
    N_will_vote_honestly = len(will_vote_honestly)

    assert len(will_vote_honestly) % 2 == 0

    # split into who will vote left/right
    force_vote_L = [ will_vote_honestly.pop() for i in range(N_will_vote_honestly // 2) ]
    force_vote_R = [ will_vote_honestly.pop() for i in range(N_will_vote_honestly // 2) ]

    assert len(will_vote_honestly) == 0

    # get the `swayers' from slot (i-1) for slot i
    swayers = cm_adv_prev & adv_swayers_during_epoch0
    assert len(swayers) == 2

    # assign `swayer' roles
    swayer_L = swayers.pop()
    swayer_R = swayers.pop()
    assert len(swayers) == 0

    # these are the local views on LMD after the `swayers' have cast their `late' (withheld) vote from slot (i-1)
    lmd_swayed_L = copy.copy(lmd)
    lmd_swayed_R = copy.copy(lmd)
    lmd_swayed_L[swayer_L] = VOTED_L
    lmd_swayed_R[swayer_R] = VOTED_R

    # make sure in the local views the respective left/right votes are leading
    assert leading(lmd_swayed_L) == VOTED_L
    assert leading(lmd_swayed_R) == VOTED_R

    # vote left
    for i in force_vote_L:
        lmd[i] = VOTED_L

    # vote right
    for i in force_vote_R:
        lmd[i] = VOTED_R

    # reflect `swayer' votes globally
    lmd[swayer_L] = VOTED_L
    lmd[swayer_R] = VOTED_R

    print(f"slot {slot} balance:", balance(lmd))
    assert not leading(lmd)


# SLOT C .. \infty (EPOCH 1 AND BEYOND):

for slot in range(scenario.C, NUM_SLOTS_SIMULATE):
    (cm_adv_prev, cm_hon_prev) = schedule.committee_fractions_for_slot(slot % scenario.C)
    (cm_adv_cur, cm_hon_cur) = schedule.committee_fractions_for_slot(slot)

    # `fillers' continue to vote honestly
    will_vote_honestly = cm_hon_cur | (cm_adv_cur & adv_fillers_during_epoch0)

    # all validators should stick to their previous votes
    force_vote_L = [ i for i in will_vote_honestly if lmd[i] == VOTED_L ]
    force_vote_R = [ i for i in will_vote_honestly if lmd[i] == VOTED_R ]

    assert len(will_vote_honestly) == len(force_vote_L) + len(force_vote_R)

    # get `swayers' for this slot (for epoch 2 and beyond, they might not be
    # in the same slot in the epoch before anymore, but that does not matter)
    swayers = cm_adv_prev & adv_swayers_during_epoch1
    assert len(swayers) == 2

    swayer_1 = swayers.pop()
    swayer_2 = swayers.pop()
    assert len(swayers) == 0

    if scenario.slot_to_epoch(slot)[0] == 1:
        # during epoch 1, the `swayers' for epoch 1 and beyond have not voted yet
        assert (lmd[swayer_1], lmd[swayer_2]) == (VOTED_N, VOTED_N)
        swayer_L = swayer_1
        swayer_R = swayer_2

    elif scenario.slot_to_epoch(slot)[0] >= 2:
        # during epoch 2 and beyond, the `swayers' for epoch 1 and beyond are guaranteed
        # to have voted on opposing chains
        assert (lmd[swayer_1], lmd[swayer_2]) in ((VOTED_L, VOTED_R), (VOTED_R, VOTED_L))

        # make the `swayers' switch sides, so that they can sway votes
        if (lmd[swayer_1], lmd[swayer_2]) == (VOTED_L, VOTED_R):
            swayer_L = swayer_2
            swayer_R = swayer_1
        elif (lmd[swayer_1], lmd[swayer_2]) == (VOTED_R, VOTED_L):
            swayer_L = swayer_1
            swayer_R = swayer_2
        else:
            assert False

    # these are the local views on LMD after the `swayers' have cast their
    # `late' (withheld) vote from the previous epoch
    lmd_swayed_L = copy.copy(lmd)
    lmd_swayed_R = copy.copy(lmd)
    lmd_swayed_L[swayer_L] = VOTED_L
    lmd_swayed_R[swayer_R] = VOTED_R

    # make sure in the local views the respective left/right votes are leading
    assert leading(lmd_swayed_L) == VOTED_L
    assert leading(lmd_swayed_R) == VOTED_R

    # vote left
    for i in force_vote_L:
        lmd[i] = VOTED_L

    # vote right
    for i in force_vote_R:
        lmd[i] = VOTED_R

    # reflect `swayer' votes globally
    lmd[swayer_L] = VOTED_L
    lmd[swayer_R] = VOTED_R

    print(f"slot {slot} balance:", balance(lmd))
    assert not leading(lmd)


print("liveness attack successful!")
