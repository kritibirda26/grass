# -*- coding: utf-8 -*-
"""
Created on Thu Jun 19 14:13:53 2014

@author: pietro
"""
import sys
import unittest
import numpy as np

from grass.gunittest.case import TestCase
from grass.gunittest.main import test

import grass.lib.vector as libvect
from grass.script.core import run_command

from grass.pygrass.vector import VectorTopo
from grass.pygrass.vector.geometry import Point, Line, Node


class PointTestCase(TestCase):

    def test_empty_init(self):
        """Test Point()"""
        point = Point()
        self.assertEqual(point.gtype, libvect.GV_POINT)
        self.assertEqual(point.x, 0)
        self.assertEqual(point.y, 0)
        self.assertIsNone(point.z)
        self.assertTrue(point.is2D)

    def test_init_3d(self):
        """Test 3D Point(1, 2, 3)"""
        point = Point(1, 2, 3)
        self.assertEqual(point.x, 1)
        self.assertEqual(point.y, 2)
        self.assertEqual(point.z, 3)
        self.assertFalse(point.is2D)

    def test_switch_2D_3D_2D(self):
        """Test switch between: 2D => 3D => 2D"""
        point = Point()
        self.assertIsNone(point.z)
        self.assertTrue(point.is2D)
        point.z = 1
        self.assertFalse(point.is2D)
        point.z = None
        self.assertTrue(point.is2D, True)

    def test_coords(self):
        """Test coords method"""
        self.assertEqual(Point(1, 2).coords(), (1, 2))
        self.assertEqual(Point(1, 2, 3).coords(), (1, 2, 3))

    def test_to_wkt(self):
        """Test coords method"""
        self.assertEqual(Point(1, 2).to_wkt(), 'POINT(1.000000 2.000000)')
        self.assertEqual(Point(1, 2, 3).to_wkt(),
                         'POINT(1.000000 2.000000 3.000000)')

    def test_distance(self):
        """Test distance method"""
        point0 = Point(0, 0, 0)
        point1 = Point(1, 0)
        self.assertEqual(point0.distance(point1), 1.0)
        point1.z = 1
        self.assertAlmostEqual(point0.distance(point1), np.sqrt(2.))

    def test_eq(self):
        """Test __eq__"""
        point0 = Point(0, 0)
        point1 = Point(1, 0)
        self.assertFalse(point0 == point1)
        self.assertFalse(point0 == (1, 0))
        self.assertTrue(point0 == point0)
        self.assertTrue(point0 == (0, 0))

    def test_repr(self):
        """Test __eq__"""
        self.assertEqual(repr(Point(1, 2)), 'Point(1.000000, 2.000000)')
        self.assertEqual(repr(Point(1, 2, 3)),
                         'Point(1.000000, 2.000000, 3.000000)')

    @unittest.skip("Not implemented yet.")
    def test_buffer(self):
        """Test buffer method"""
        # TODO: verify if the buffer depends from the mapset's projection
        pass


class LineTestCase(TestCase):

    tmpname = "LineTestCase_map"

    @classmethod
    def setUpClass(cls):
        
        from grass.pygrass import utils
        utils.create_test_vector_map(cls.tmpname)
        
        cls.vect = None
        cls.vect = VectorTopo(cls.tmpname)
        cls.vect.open('r')
        cls.c_mapinfo = cls.vect.c_mapinfo

    @classmethod
    def tearDownClass(cls):
        if cls.vect is not None:
            cls.vect.close()
            cls.c_mapinfo = None

        """Remove the generated vector map, if exist"""
        from grass.pygrass.utils import get_mapset_vector
        mset = get_mapset_vector(cls.tmpname, mapset='')
        if mset:
            run_command("g.remove", flags='f', type='vector', name=cls.tmpname)

    def test_len(self):
        """Test __len__ magic method"""
        self.assertEqual(len(Line()), 0)
        self.assertEqual(len(Line([(0, 0), (1, 1)])), 2)

    @unittest.skipIf(sys.version_info[:2] < (2, 7), "Require Python >= 2.7")
    def test_getitem(self):
        """Test __getitem__ magic method"""
        line = Line([(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)])
        self.assertTupleEqual(line[0].coords(), (0, 0))
        self.assertTupleEqual(line[1].coords(), (1, 1))
        self.assertTupleEqual(line[-2].coords(), (3, 3))
        self.assertTupleEqual(line[-1].coords(), (4, 4))
        self.assertListEqual([p.coords() for p in line[:2]], [(0, 0), (1, 1)])
        self.assertListEqual([p.coords() for p in line[::2]],
                             [(0, 0), (2, 2), (4, 4)])
        with self.assertRaises(IndexError):
            line[5]

    @unittest.skipIf(sys.version_info[:2] < (2, 7), "Require Python >= 2.7")
    def test_setitem(self):
        """Test __setitem__ magic method"""
        line = Line([(0, 0), (1, 1)])
        self.assertTupleEqual(line[0].coords(), (0., 0.))
        line[0] = (10, 10)
        self.assertTupleEqual(line[0].coords(), (10., 10.))

    @unittest.skipIf(sys.version_info[:2] < (2, 7), "Require Python >= 2.7")
    def test_get_pnt(self):
        """Test get_pnt method"""
        line = Line([(0, 0), (1, 1)])
        with self.assertRaises(ValueError):
            line.point_on_line(5)
        vals = (0.7071067811865475, 0.7071067811865475)
        self.assertTupleEqual(line.point_on_line(1).coords(), vals)

    def test_bbox(self):
        """Test bbox method"""
        line = Line([(0, 10), (0, 11), (1, 11), (1, 10)])
        bbox = line.bbox()
        self.assertEqual(11, bbox.north)
        self.assertEqual(10, bbox.south)
        self.assertEqual(1, bbox.east)
        self.assertEqual(0, bbox.west)

    def test_nodes(self):
        """Test nodes method"""
        def nodes2tuple(nodes):
            """Convert an iterable of nodes to a tuple of nodes id"""
            return tuple(n.id for n in nodes)

        with VectorTopo("LineTestCase_map", mode='r') as vect:
            self.assertTupleEqual((1, 2), nodes2tuple(vect[4].nodes()))
            self.assertTupleEqual((3, 4), nodes2tuple(vect[5].nodes()))
            self.assertTupleEqual((5, 6), nodes2tuple(vect[6].nodes()))

class NodeTestCase(TestCase):
    
    tmpname = "NodeTestCase_map"

    @classmethod
    def setUpClass(cls):
        
        from grass.pygrass import utils
        utils.create_test_vector_map(cls.tmpname)
        
        cls.vect = None
        cls.vect = VectorTopo(cls.tmpname)
        cls.vect.open('r')
        cls.c_mapinfo = cls.vect.c_mapinfo

    @classmethod
    def tearDownClass(cls):
        if cls.vect is not None:
            cls.vect.close()
            cls.c_mapinfo = None

        """Remove the generated vector map, if exist"""
        from grass.pygrass.utils import get_mapset_vector
        mset = get_mapset_vector(cls.tmpname, mapset='')
        if mset:
            run_command("g.remove", flags='f', type='vector', name=cls.tmpname)

    def test_init(self):
        """Test Node __init__"""
        node = Node(v_id=4, c_mapinfo=self.c_mapinfo)
        self.assertEqual(4, node.id)
        self.assertTrue(node.is2D)
        self.assertEqual(1, node.nlines)

    def test_coords(self):
        """Test Node coordinates"""
        node = Node(v_id=4, c_mapinfo=self.c_mapinfo)
        self.assertTupleEqual((12.0, 0.0),
                              node.coords())

    def test_ilines(self):
        """Test Node coordinates"""
        node = Node(v_id=4, c_mapinfo=self.c_mapinfo) # Line 5 ends in this node
        self.assertTupleEqual((-5,), tuple(node.ilines())) 
        self.assertTupleEqual((-5,), tuple(node.ilines(only_in=True)))
        node = Node(v_id=3, c_mapinfo=self.c_mapinfo) # Line 5 starts at this node
        self.assertTupleEqual((5,), tuple(node.ilines(only_out=True)))

    def test_angles(self):
        """Test Node angles"""
        node = Node(v_id=4, c_mapinfo=self.c_mapinfo)
        angles = (1.5707963705062866,) # 90°
        self.assertTupleEqual(angles, tuple(node.angles()))

if __name__ == '__main__':
    test()
