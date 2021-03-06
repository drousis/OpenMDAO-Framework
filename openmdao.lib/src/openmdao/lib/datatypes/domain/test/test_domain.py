"""
Test :class:`DomainObj` operations.
"""

import logging
import unittest

import numpy

from openmdao.lib.datatypes.domain import DomainObj, FlowSolution, \
                                       GridCoordinates, Vector, Zone, \
                                       write_plot3d_q

from openmdao.lib.datatypes.domain.test.wedge import create_wedge_3d, \
                                                  create_wedge_2d
from openmdao.util.testutil import assert_raises


class TestCase(unittest.TestCase):
    """ Test :class:`DomainObj` operations. """

    def test_domain(self):
        logging.debug('')
        logging.debug('test_domain')

        logger = logging.getLogger()
        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30., 'x')

        domain = DomainObj()
        self.assertEqual(domain.reference_state, None)
        self.assertEqual(domain.zones, [])
        self.assertEqual(domain.shape, [])
        self.assertEqual(domain.extent, [])

        self.assertFalse(domain.is_equivalent([], logger))

        domain.add_domain(wedge, make_copy=True)
        self.assertTrue(domain.is_equivalent(wedge))
        self.assertEqual(domain.shape, [(30, 20, 10)])
        self.assertEqual(domain.extent[0][:2], (0., 5.))
        self.assertEqual(domain.xyzzy.flow_solution.momentum.shape,
                         (30, 20, 10))
        self.assertEqual(domain.xyzzy.flow_solution.momentum.extent[:2],
                         (0., 5.))

        domain.rename_zone('wedge', domain.xyzzy)
        self.assertFalse(domain.is_equivalent(wedge, logger))

        domain = wedge.copy()
        zone = domain.remove_zone('xyzzy')
        self.assertFalse(domain.is_equivalent(wedge, logger))
        domain.add_zone('xyzzy', zone)
        self.assertTrue(domain.is_equivalent(wedge, logger))

        # Translations ordered for test coverage.
        domain.translate(0., 0., 0.5)
        self.assertFalse(domain.is_equivalent(wedge, logger))

        domain.translate(0., 1., 0.)
        self.assertFalse(domain.is_equivalent(wedge, logger))

        domain.translate(2.5, 0., 0.)
        self.assertFalse(domain.is_equivalent(wedge, logger))

        domain.rotate_about_x(90.)

        domain.add_domain(wedge)
        self.assertEqual(domain.shape, [(30, 20, 10), (30, 20, 10)])

        # Uncomment to visualize result.
#        write_plot3d_q(domain, 'doubled.xyz', 'doubled.q')

        domain.rotate_about_y(90.)
        domain.rotate_about_z(90.)

        domain.deallocate()
        self.assertEqual(domain.shape, [])
        self.assertEqual(domain.extent, [])

        domain = wedge.copy()

        assert_raises(self, "domain.add_zone('xyzzy', wedge)",
                      globals(), locals(), ValueError,
                      "name 'xyzzy' is already bound")

        assert_raises(self, "domain.rename_zone('xyzzy', domain.xyzzy)",
                      globals(), locals(), ValueError,
                      "name 'xyzzy' is already bound")

    def test_coordinate_systems(self):
        logging.debug('')
        logging.debug('test_coordinate_systems')

        logger = logging.getLogger()
        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30.)

        domain = wedge.copy()
        domain.make_left_handed()
        tmp = wedge.xyzzy.grid_coordinates.z * -1.
        self.assertTrue((domain.xyzzy.grid_coordinates.z == tmp).all())
        self.assertFalse(domain.is_equivalent(wedge, logger))

        domain.make_right_handed()
        self.assertTrue(domain.is_equivalent(wedge, logger))

        cyl = wedge.copy()
        cyl.make_cylindrical()

        cart = cyl.copy()
        cart.make_cartesian()
        self.assertTrue(cart.is_equivalent(wedge, tolerance=0.000001))

        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30., 'x')

        cyl = wedge.copy()
        cyl.make_cylindrical('x')

        cart = cyl.copy()
        cart.make_cartesian('x')
        self.assertTrue(cart.is_equivalent(wedge, tolerance=0.000001))

    def test_flow(self):
        logging.debug('')
        logging.debug('test_flow')

        logger = logging.getLogger()

        flow = FlowSolution()
        self.assertEqual(flow.grid_location, 'Vertex')
        self.assertEqual(flow.ghosts, [0, 0, 0, 0, 0, 0])

        self.assertFalse(flow.is_equivalent([], logger))

        other = FlowSolution()
        self.assertTrue(flow.is_equivalent(other, logger))
        other.grid_location = 'CellCenter'
        self.assertFalse(flow.is_equivalent(other, logger))
        other.grid_location = 'Vertex'
        other.ghosts = [1, 1, 1, 1, 1, 1]
        self.assertFalse(flow.is_equivalent(other, logger))

        assert_raises(self, "flow.grid_location = 'pluto'",
                      globals(), locals(), ValueError,
                      "'pluto' is not a valid grid location", use_exec=True)

        assert_raises(self, "flow.ghosts = []",
                      globals(), locals(), ValueError,
                      'ghosts must be a 6-element array', use_exec=True)

        assert_raises(self, "flow.ghosts = [1, 2, 3, 4, 5, -6]",
                      globals(), locals(), ValueError,
                      'All ghost values must be >= 0', use_exec=True)

        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30.)
        domain = wedge.copy()

        assert_raises(self,
                      "domain.xyzzy.flow_solution.add_array('density',"
                      " numpy.zeros(domain.xyzzy.shape, numpy.float32))",
                      globals(), locals(), ValueError,
                      "name 'density' is already bound")

        assert_raises(self,
                      "domain.xyzzy.flow_solution.add_vector('momentum',"
                      " numpy.zeros(domain.xyzzy.shape, numpy.float32))",
                      globals(), locals(), ValueError,
                      "name 'momentum' is already bound")

        self.assertTrue(domain.is_equivalent(wedge, logger))
        pressure = wedge.xyzzy.flow_solution.density.copy()
        domain.xyzzy.flow_solution.add_array('pressure', pressure)
        self.assertFalse(domain.is_equivalent(wedge, logger))

        pressure2 = wedge.xyzzy.flow_solution.density.copy()
        wedge.xyzzy.flow_solution.add_array('pressure', pressure2)
        self.assertTrue(domain.is_equivalent(wedge, logger))

        domain.xyzzy.flow_solution.add_vector('empty', Vector())
        self.assertFalse(domain.is_equivalent(wedge, logger))

        pressure2[0][0][0] += 1.
        self.assertFalse(domain.is_equivalent(wedge, logger))
        self.assertFalse(domain.is_equivalent(wedge, logger, tolerance=0.00001))
 
    def test_grid(self):
        logging.debug('')
        logging.debug('test_grid')

        logger = logging.getLogger()

        grid = GridCoordinates()
        self.assertEqual(grid.shape, ())
        self.assertEqual(grid.extent, ())
        self.assertEqual(grid.ghosts, [0, 0, 0, 0, 0, 0])

        self.assertFalse(grid.is_equivalent([], logger))

        other = GridCoordinates()
        self.assertTrue(grid.is_equivalent(other, logger))
        other.ghosts = [1, 1, 1, 1, 1, 1]
        self.assertFalse(grid.is_equivalent(other, logger))

        assert_raises(self, 'grid.ghosts = []', globals(), locals(),
                      ValueError, 'ghosts must be a 6-element array',
                      use_exec=True)

        assert_raises(self, 'grid.ghosts = [0, 1, 2, 3, 4, -5]',
                      globals(), locals(), ValueError,
                      'All ghost values must be >= 0', use_exec=True)

        assert_raises(self, 'grid.translate(1., 0., 0.)',
                      globals(), locals(), AttributeError, 'no X coordinates')

        assert_raises(self, 'grid.translate(0., 1., 0.)',
                      globals(), locals(), AttributeError, 'no Y coordinates')

        assert_raises(self, 'grid.translate(0., 0., 1.)',
                      globals(), locals(), AttributeError, 'no Z coordinates')

        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30.)
        assert_raises(self,
                      "wedge.xyzzy.grid_coordinates.make_cylindrical(axis='q')",
                      globals(), locals(), ValueError,
                      "axis must be 'z' or 'x'")
        wedge.xyzzy.grid_coordinates.make_cylindrical(axis='z')
        assert_raises(self,
                      "wedge.xyzzy.grid_coordinates.make_cartesian(axis='q')",
                      globals(), locals(), ValueError,
                      "axis must be 'z' or 'x'")
        wedge.xyzzy.grid_coordinates.make_cartesian(axis='z')

    def test_vector(self):
        logging.debug('')
        logging.debug('test_vector')

        logger = logging.getLogger()

        vec = Vector()
        self.assertEqual(vec.x, None)
        self.assertEqual(vec.y, None)
        self.assertEqual(vec.z, None)
        self.assertEqual(vec.r, None)
        self.assertEqual(vec.t, None)
        self.assertEqual(vec.shape, ())
        self.assertEqual(vec.extent, ())

        self.assertFalse(vec.is_equivalent([], 'vec', logger))

        assert_raises(self, 'vec.flip_z()', globals(), locals(),
                      AttributeError, 'flip_z: no Z component')

        assert_raises(self, 'vec.rotate_about_x(0.)', globals(), locals(),
                      AttributeError, 'rotate_about_x: no Y component')

        assert_raises(self, 'vec.rotate_about_y(0.)', globals(), locals(),
                      AttributeError, 'rotate_about_y: no X component')

        assert_raises(self, 'vec.rotate_about_z(0.)', globals(), locals(),
                      AttributeError, 'rotate_about_z: no X component')

        wedge = create_wedge_2d((20, 10), 0.5, 2., 30.)
        vec = wedge.xyzzy.flow_solution.momentum
        assert_raises(self, 'vec.rotate_about_x(0.)', globals(), locals(),
                      AttributeError, 'rotate_about_x: no Z component')

        assert_raises(self, 'vec.rotate_about_y(0.)', globals(), locals(),
                      AttributeError, 'rotate_about_y: no Z component')

        self.assertEqual(len(vec.extent), 4)
        wedge.make_cylindrical()
        self.assertEqual(vec.extent[:2], (0.5, 2.))

        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30.)
        grid = wedge.xyzzy.grid_coordinates
        grid.make_cylindrical(axis='z')
        vec = wedge.xyzzy.flow_solution.momentum
        assert_raises(self, "vec.make_cylindrical(grid, axis='q')",
                      globals(), locals(), ValueError,
                      "axis must be 'z' or 'x'")
        assert_raises(self, "vec.make_cartesian(grid, axis='q')",
                      globals(), locals(), ValueError,
                      "axis must be 'z' or 'x'")
        grid.make_cartesian(axis='z')

        domain = wedge.copy()
        domain.xyzzy.flow_solution.momentum.z += 1.
        self.assertFalse(domain.is_equivalent(wedge, logger))
        self.assertFalse(domain.is_equivalent(wedge, logger, tolerance=0.00001))

        domain = wedge.copy()
        grid = domain.xyzzy.grid_coordinates
        grid.make_cylindrical(axis='z')
        vec = domain.xyzzy.flow_solution.momentum
        vec.make_cylindrical(grid)
        self.assertFalse(vec.is_equivalent(wedge.xyzzy.flow_solution.momentum,
                                           'momentum', logger))
        self.assertEqual(vec.extent, (0., 5., 0., 5., -2.5, 0.))

    def test_zone(self):
        logging.debug('')
        logging.debug('test_zone')

        logger = logging.getLogger()

        zone = Zone()
        self.assertEqual(zone.reference_state, None)
        self.assertEqual(zone.coordinate_system, 'Cartesian')
        self.assertEqual(zone.right_handed, True)
        self.assertEqual(zone.symmetry, None)
        self.assertEqual(zone.symmetry_axis, None)
        self.assertEqual(zone.symmetry_instances, 1)
        self.assertEqual(zone.shape, ())
        self.assertEqual(zone.extent, ())

        self.assertFalse(zone.is_equivalent([], logger))

        assert_raises(self, "zone.coordinate_system = 'pluto'",
                      globals(), locals(), ValueError,
                      "invalid coordinate system 'pluto'", use_exec=True)

        wedge = create_wedge_3d((30, 20, 10), 5., 0.5, 2., 30.)
        domain = wedge.copy()

        domain.xyzzy.symmetry_instances = 5
        self.assertFalse(domain.is_equivalent(wedge))

        domain.xyzzy.symmetry_axis = 'x'
        self.assertFalse(domain.is_equivalent(wedge))

        domain.xyzzy.symmetry = 'rotational'
        self.assertFalse(domain.is_equivalent(wedge))

        domain.make_cylindrical()
        self.assertFalse(domain.is_equivalent(wedge))
        assert_raises(self, 'domain.translate(0., 0., 0.)', globals(), locals(),
                      RuntimeError, 'Zone not in cartesian coordinates')
        assert_raises(self, 'domain.rotate_about_x(0.)', globals(), locals(),
                      RuntimeError, 'Zone not in cartesian coordinates')
        assert_raises(self, 'domain.rotate_about_y(0.)', globals(), locals(),
                      RuntimeError, 'Zone not in cartesian coordinates')
        assert_raises(self, 'domain.rotate_about_z(0.)', globals(), locals(),
                      RuntimeError, 'Zone not in cartesian coordinates')


if __name__ == '__main__':
    import nose
    import sys
    sys.argv.append('--cover-package=openmdao.lib.datatypes.domain')
    sys.argv.append('--cover-erase')
    nose.runmodule()

