# A Bouncing Attack on Gasper

In our manuscript [Ebb-and-Flow] we describe a bouncing-style attack on the Gasper consensus protocol [Gasper] in a synchronous network.
This repository contains the source code for the simulation of this attack.
For a detailed description of the attack, see Section II and Appendix A of our manuscript [Ebb-and-Flow].
For the source code of the simulations presented in [Ebb-and-Flow], please see: [https://github.com/tse-group/ebb-and-flow](https://github.com/tse-group/ebb-and-flow)


## Attack on Gasper

The file `gasper-attack-simplified.py` contains a simulation of the Gasper protocol in a synchronous network
as well as the adversarial actions for the attack, written in Python. See the extensive code comments
for details on what the adversary does when and why.


## References

* [Ebb-and-Flow]<br/>
  **Ebb-and-Flow Protocols: A Resolution of the Availability-Finality Dilemma**<br/>
  Joachim Neu, Ertem Nusret Tas, David Tse<br/>
  [arXiv:2009.04987](https://arxiv.org/abs/2009.04987)

* [Gasper]<br/>
  **Combining GHOST and Casper**<br/>
  Vitalik Buterin, Diego Hernandez, Thor Kamphefner, Khiem Pham, Zhi Qiao, Danny Ryan, Juhyeok Sin, Ying Wang, Yan X Zhang<br/>
  [arXiv:2003.03052](https://arxiv.org/abs/2003.03052)

