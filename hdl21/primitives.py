"""
# Hdl21 Primitive Modules

Primitives are leaf-level Modules typically defined not by users, 
but by simulation tools or device fabricators. 
Prominent examples include MOS transistors, diodes, resistors, and capacitors. 

Primitives divide in two classes, `physical` and `ideal`, 
indicated by their `primtype` attribute. 
`PrimitiveType.IDEAL` primitives specify circuit-theoretic ideal elements 
e.g. resistors, capacitors, inductors, and notably aphysical elements 
such as ideal voltage and current sources. 
`PrimitiveType.PHYSICAL` primitives in contrast specify abstract versions 
of ultimately physically-realizable elements such as transistors and diodes. 
These elements typically require some external translation, e.g. by a process-technology 
library, to execute in simulations or to be realized in hardware. 

Many element-types (particularly passives) come in both `ideal` and `physical` flavors, 
as typical process-technologies include physical passives, but with far different 
parameterization than ideal passives. For example resistors are commonly specified 
in physical length and width. Capacitors are similarly specified in physical terms, 
often adding metal layers or other physical features. The component-value (R,C,L, etc.) 
for these physically-specified cells is commonly suggestive or optional. 

| Physical           | Ideal          | Alias(es)         | 
| ------------------ | -------------- | ----------------- | 
| PhysicalResistor   | IdealResistor  | R, Res, Resistor  | 
| PhysicalInductor   | IdealInductor  | L, Ind, Inductor  | 
| PhysicalCapacitor  | IdealCapacitor | C, Cap, Capacitor | 
| PhysicalShort      | IdealShort     | Short             | 
|                    | VoltageSource  | Vsrc, V           | 
|                    | CurrentSource  | Isrc, I           | 
| Mos                |                |                   | 
| Diode              |                | D                 | 

"""

from pydantic.dataclasses import dataclass
from dataclasses import replace
from enum import Enum
from typing import Optional, Any, List, Type, Union

# Local imports
from .params import paramclass, Param, isparamclass, HasNoParams
from .signal import Port, Signal, Visibility
from .instance import calls_instantiate


class PrimitiveType(Enum):
    """ Enumerated Primitive-Types """

    IDEAL = "IDEAL"
    PHYSICAL = "PHYSICAL"


@dataclass
class Primitive:
    """# hdl21 Primitive Component

    Primitives are leaf-level Modules typically defined not by users,
    but by simulation tools or device fabricators.
    Prominent examples include MOS transistors, diodes, resistors, and capacitors.
    """

    name: str
    desc: str
    port_list: List[Signal]
    paramtype: Type
    primtype: PrimitiveType

    def __post_init_post_parse__(self):
        """After type-checking, do plenty more checks on values"""
        if not isparamclass(self.paramtype):
            raise TypeError(
                f"Invalid Primitive param-type {self.paramtype} for {self.name}, must be an `hdl21.paramclass`"
            )
        for p in self.port_list:
            if not p.name:
                raise ValueError(f"Unnamed Primitive Port {p} for {self.name}")
            if p.vis != Visibility.PORT:
                raise ValueError(
                    f"Invalid Primitive Port {p.name} on {self.name}; must have PORT visibility"
                )

    def __call__(self, params: Any) -> "PrimitiveCall":
        return PrimitiveCall(prim=self, params=params)

    @property
    def Params(self) -> Type:
        return self.paramtype

    @property
    def ports(self) -> dict:
        return {p.name: p for p in self.port_list}


@calls_instantiate
@dataclass
class PrimitiveCall:
    """Primitive Call
    A combination of a Primitive and its Parameter-values,
    typically generated by calling the Primitive."""

    prim: Primitive
    params: Any

    def __post_init_post_parse__(self):
        # Type-validate our parameters
        if not isinstance(self.params, self.prim.paramtype):
            raise TypeError(
                f"Invalid parameters {self.params} for Primitive {self.prim}. Must be {self.prim.paramtype}"
            )

    @property
    def ports(self) -> dict:
        return self.prim.ports


class MosType(Enum):
    """NMOS/PMOS Type Enumeration"""

    NMOS = "NMOS"
    PMOS = "PMOS"


class MosVth(Enum):
    """MOS Threshold Enumeration"""

    STD = "STD"
    LOW = "LOW"
    HIGH = "HIGH"


@paramclass
class MosParams:
    """MOS Transistor Parameters"""

    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)
    nser = Param(dtype=int, desc="Number of series fingers", default=1)
    npar = Param(dtype=int, desc="Number of parallel fingers", default=1)
    tp = Param(dtype=MosType, desc="MosType (PMOS/NMOS)", default=MosType.NMOS)
    vth = Param(dtype=MosVth, desc="Threshold voltage specifier", default=MosVth.STD)

    def __post_init_post_parse__(self):
        """Value Checks"""
        if self.w <= 0:
            raise ValueError(f"MosParams with invalid width {self.w}")
        if self.l <= 0:
            raise ValueError(f"MosParams with invalid length {self.l}")
        if self.npar <= 0:
            raise ValueError(
                f"MosParams with invalid number parallel fingers {self.npar}"
            )
        if self.nser <= 0:
            raise ValueError(
                f"MosParams with invalid number series fingers {self.nser}"
            )


Mos = Primitive(
    name="Mos",
    desc="Mos Transistor",
    port_list=[Port(name="d"), Port(name="g"), Port(name="s"), Port(name="b")],
    paramtype=MosParams,
    primtype=PrimitiveType.PHYSICAL,
)


def Nmos(params: MosParams) -> Primitive:
    """Nmos Constructor. A thin wrapper around `hdl21.primitives.Mos`"""
    return Mos(replace(params, tp=MosType.NMOS))


def Pmos(params: MosParams) -> Primitive:
    """Pmos Constructor. A thin wrapper around `hdl21.primitives.Mos`"""
    return Mos(replace(params, tp=MosType.PMOS))


@paramclass
class DiodeParams:
    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)

    # FIXME: will likely want a similar type-switch, at least eventually
    # tp = Param(dtype=Tbd!, desc="Diode type specifier")


Diode = Primitive(
    name="Diode",
    desc="Diode",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=DiodeParams,
    primtype=PrimitiveType.PHYSICAL,
)


# Common alias(es)
D = Diode


@paramclass
class ResistorParams:
    r = Param(dtype=float, desc="Resistance (ohms)")


IdealResistor = Primitive(
    name="IdealResistor",
    desc="Ideal Resistor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=ResistorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common aliases
R = Res = Resistor = IdealResistor


@paramclass
class PhysicalResistorParams:
    r = Param(dtype=float, desc="Resistance (ohms)")


PhysicalResistor = Primitive(
    name="PhysicalResistor",
    desc="Physical Resistor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=ResistorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class IdealCapacitorParams:
    c = Param(dtype=float, desc="Capacitance (F)")


IdealCapacitor = Primitive(
    name="IdealCapacitor",
    desc="Ideal Capacitor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=IdealCapacitorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common aliases
C = Cap = Capacitor = IdealCapacitor


@paramclass
class PhysicalCapacitorParams:
    c = Param(dtype=float, desc="Capacitance (F)")


PhysicalCapacitor = Primitive(
    name="PhysicalCapacitor",
    desc="Physical Capacitor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalCapacitorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class IdealInductorParams:
    l = Param(dtype=float, desc="Inductance (H)")


IdealInductor = Primitive(
    name="IdealInductor",
    desc="Ideal Inductor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=IdealInductorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common alias(es)
L = Inductor = IdealInductor


@paramclass
class PhysicalInductorParams:
    l = Param(dtype=float, desc="Inductance (H)")


PhysicalInductor = Primitive(
    name="PhysicalInductor",
    desc="Physical Inductor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalInductorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class PhysicalShortParams:
    layer = Param(dtype=Optional[int], desc="Metal layer", default=None)
    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)


PhysicalShort = Primitive(
    name="PhysicalShort",
    desc="Short-Circuit/ Net-Tie",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalShortParams,
    primtype=PrimitiveType.PHYSICAL,
)

IdealShort = Primitive(
    name="IdealShort",
    desc="Short-Circuit/ Net-Tie",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=HasNoParams,
    primtype=PrimitiveType.IDEAL,
)

Short = IdealShort


# Type alias for many scalar parameters
ScalarParam = Union[int, float, str]
ScalarOption = Optional[ScalarParam]


@paramclass
class VoltageSourceParams:
    dc = Param(dtype=ScalarOption, default=0, desc="DC Value (V)")
    delay = Param(dtype=ScalarOption, default=None, desc="Time Delay (s)")

    # Pulse source parameters
    v0 = Param(dtype=ScalarOption, default=None, desc="Zero Value (V)")
    v1 = Param(dtype=ScalarOption, default=None, desc="One Value (V)")
    period = Param(dtype=ScalarOption, default=None, desc="Period (s)")
    rise = Param(dtype=ScalarOption, default=None, desc="Rise time (s)")
    fall = Param(dtype=ScalarOption, default=None, desc="Fall time (s)")
    width = Param(dtype=ScalarOption, default=None, desc="Pulse width (s)")


VoltageSource = Primitive(
    name="VoltageSource",
    desc="Ideal Voltage Source",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=VoltageSourceParams,
    primtype=PrimitiveType.IDEAL,
)

V = Vsrc = VoltageSource


@paramclass
class CurrentSourceParams:
    dc = Param(dtype=ScalarOption, default=0, desc="DC Value (A)")


CurrentSource = Primitive(
    name="CurrentSource",
    desc="Ideal Current Source",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=CurrentSourceParams,
    primtype=PrimitiveType.IDEAL,
)

I = Isrc = CurrentSource

