from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import compas
import compas_rbe

from compas_assembly.datastructures import Assembly
from compas_assembly.interfaces import assembly_interfaces_bestfit
from compas_assembly.interfaces import planarize_interfaces
from compas_assembly.viewer import AssemblyViewer

from compas_rbe.equilibrium import compute_interface_forces


# initialize assembly and blocks from json file

assembly = Assembly.from_json(compas_rbe.get('simple_stack_curvedsrf2.json'))

# print(list(assembly.vertices_where({'is_support': True})))

# identify block interfaces and update block_model

assembly_interfaces_bestfit(
    assembly,
    nmax=10,
    tmax=0.5,
    amin=0.01,
    lmin=0.01,
)

# TODO: Planerize all interfaces first before compute interface forces
# planarize_interfaces(assembly.edge)

# equilibrium
compute_interface_forces(assembly, solver='MOSEK', verbose=True)

# result

viewer = AssemblyViewer()
viewer.assembly = assembly
viewer.show()
