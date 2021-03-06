# pylint: disable-msg=C0111,C0103

import unittest
import logging
import nose

from openmdao.main.api import Assembly, Component, Driver, set_as_top, Dataflow
from openmdao.lib.datatypes.api import Int
from openmdao.main.hasobjective import HasObjectives
from openmdao.main.hasconstraints import HasConstraints
from openmdao.main.hasparameters import HasParameters
from openmdao.util.decorators import add_delegate

exec_order = []

@add_delegate(HasObjectives, HasParameters, HasConstraints)
class DumbDriver(Driver):
    def execute(self):
        global exec_order
        exec_order.append(self.name)
        super(DumbDriver, self).execute()


class Simple(Component):
    a = Int(iotype='in')
    b = Int(iotype='in')
    c = Int(iotype='out')
    d = Int(iotype='out')
    
    def __init__(self):
        super(Simple, self).__init__()
        self.a = 1
        self.b = 2
        self.c = 3
        self.d = -1

    def execute(self):
        global exec_order
        exec_order.append(self.name)
        self.c = self.a + self.b
        self.d = self.a - self.b

allcomps = ['sub.comp1','sub.comp2','sub.comp3','sub.comp4','sub.comp5','sub.comp6',
            'comp7','comp8']

topouts = ['sub.c2', 'sub.c4', 'sub.d1', 'sub.d3','sub.d5'
           'comp7.c', 'comp7.d','comp8.c', 'comp8.d']

topins = ['sub.a1', 'sub.a3', 'sub.b2', 'sub.b4','sub.b6'
          'comp7.a', 'comp7.b','comp8.a', 'comp8.b']

subins = ['comp1.a', 'comp1.b',
          'comp2.a', 'comp2.b',
          'comp3.a', 'comp3.b',
          'comp4.a', 'comp4.b',
          'comp5.a', 'comp5.b',
          'comp6.a', 'comp6.b',]

subouts = ['comp1.c', 'comp1.d',
           'comp2.c', 'comp2.d',
           'comp3.c', 'comp3.d',
           'comp4.c', 'comp4.d',
           'comp5.c', 'comp5.d',
           'comp6.c', 'comp6.d',]


subvars = subins+subouts

class DependsTestCase(unittest.TestCase):

    def setUp(self):
        global exec_order
        exec_order = []
        top = set_as_top(Assembly())
        self.top = top
        top.add('sub', Assembly())
        top.add('comp7', Simple())
        top.add('comp8', Simple())
        sub = top.sub
        sub.add('comp1', Simple())
        sub.add('comp2', Simple())
        sub.add('comp3', Simple())
        sub.add('comp4', Simple())
        sub.add('comp5', Simple())
        sub.add('comp6', Simple())

        top.driver.workflow.add(['comp7', 'sub', 'comp8'])
        sub.driver.workflow.add(['comp1','comp2','comp3',
                                 'comp4','comp5','comp6'])

        sub.create_passthrough('comp1.a', 'a1')
        sub.create_passthrough('comp2.b', 'b2')
        sub.create_passthrough('comp4.b', 'b4')
        sub.create_passthrough('comp4.c', 'c4')
        sub.create_passthrough('comp6.b', 'b6')
        sub.create_passthrough('comp2.c', 'c2')
        sub.create_passthrough('comp1.d', 'd1')
        sub.create_passthrough('comp5.d', 'd5')
        
        sub.connect('comp1.c', 'comp4.a')
        sub.connect('comp5.c', 'comp1.b')
        sub.connect('comp2.d', 'comp5.b')
        sub.connect('comp3.c', 'comp5.a')
        sub.connect('comp4.d', 'comp6.a')
        
        top.connect('sub.c4', 'comp8.a')
        
        # 'auto' passthroughs
        top.connect('comp7.c', 'sub.comp3.a')
        top.connect('sub.comp3.d', 'comp8.b')

    def test_simple(self):
        top = set_as_top(Assembly())
        top.add('comp1', Simple())
        top.driver.workflow.add('comp1')
        vars = ['a','b','c','d']
        self.assertEqual(top.comp1.exec_count, 0)
        valids = top.comp1.get_valid(vars)
        self.assertEqual(valids, [True, True, False, False])
        top.run()
        self.assertEqual(top.comp1.exec_count, 1)
        self.assertEqual(top.comp1.c, 3)
        self.assertEqual(top.comp1.d, -1)
        valids = top.comp1.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        top.set('comp1.a', 5)
        valids = top.comp1.get_valid(vars)
        self.assertEqual(valids, [True, True, False, False])
        top.run()
        self.assertEqual(top.comp1.exec_count, 2)
        self.assertEqual(top.comp1.c, 7)
        self.assertEqual(top.comp1.d, 3)
        top.run()
        self.assertEqual(top.comp1.exec_count, 2) # exec_count shouldn't change
        valids = top.comp1.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        
        # now add another comp and connect them
        top.add('comp2', Simple())
        top.driver.workflow.add('comp2')
        top.connect('comp1.c', 'comp2.a')
        self.assertEqual(top.comp2.exec_count, 0)
        self.assertEqual(top.comp2.c, 3)
        self.assertEqual(top.comp2.d, -1)
        valids = top.comp2.get_valid(vars)
        self.assertEqual(valids, [False, True, False, False])
        top.run()
        self.assertEqual(top.comp1.exec_count, 2)
        self.assertEqual(top.comp2.exec_count, 1)
        self.assertEqual(top.comp2.c, 9)
        self.assertEqual(top.comp2.d, 5)
        valids = top.comp2.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        
    def test_disconnect(self):
        self.top.disconnect('comp7.c', 'sub.comp3.a')
        self.top.sub.disconnect('c4')
        self.top.disconnect('comp8')
        
    def test_disconnect2(self):
        self.assertEqual(set(self.top.sub.list_outputs(connected=True)),
                         set(['comp3.d','c4']))
        self.top.disconnect('comp8')
        self.assertEqual(self.top.sub.list_outputs(connected=True),
                         [])
        self.assertEqual(self.top.sub._depgraph.get_source('c4'), 'comp4.c')
        
    def test_lazy1(self):
        self.top.run()
        exec_counts = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1], exec_counts)
        outs = [(5,-3),(3,-1),(5,1),(7,3),(4,6),(5,1),(3,-1),(8,6)]
        newouts = []
        for comp in allcomps:
            newouts.append((self.top.get(comp+'.c'),self.top.get(comp+'.d')))
        self.assertEqual(outs, newouts)
        self.top.run()  
        # exec_count should stay at 1 for all comps
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1], 
                         [self.top.get(x).exec_count for x in allcomps])
        
    def test_lazy2(self):
        vars = ['a','b','c','d']
        self.top.run()        
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1], exec_count)
        valids = self.top.sub.comp6.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        self.top.sub.b6 = 3
        valids = self.top.sub.comp6.get_valid(vars)
        self.assertEqual(valids, [True, False, False, False])
        self.top.run()  
        # exec_count should change only for comp6
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([1, 1, 1, 1, 1, 2, 1, 1], exec_count)
        outs = [(5,-3),(3,-1),(5,1),(7,3),(4,6),(6,0),(3,-1),(8,6)]
        for comp,vals in zip(allcomps,outs):
            self.assertEqual((comp,vals[0],vals[1]), 
                             (comp,self.top.get(comp+'.c'),self.top.get(comp+'.d')))
            
    def test_lazy3(self):
        vars = ['a','b','c','d']
        self.top.run()        
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([1, 1, 1, 1, 1, 1, 1, 1], exec_count)
        valids = self.top.sub.comp3.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        self.top.comp7.a = 3
        valids = self.top.sub.comp1.get_valid(vars)
        self.assertEqual(valids, [True, False, False, False])
        valids = self.top.sub.comp2.get_valid(vars)
        self.assertEqual(valids, [True, True, True, True])
        valids = self.top.sub.comp3.get_valid(vars)
        self.assertEqual(valids, [False, True, False, False])
        valids = self.top.sub.comp4.get_valid(vars)
        self.assertEqual(valids, [False, True, False, False])
        valids = self.top.sub.comp5.get_valid(vars)
        self.assertEqual(valids, [False, True, False, False])
        valids = self.top.sub.comp6.get_valid(vars)
        self.assertEqual(valids, [False, True, False, False])
        valids = self.top.comp7.get_valid(vars)
        self.assertEqual(valids, [True, True, False, False])
        valids = self.top.comp8.get_valid(vars)
        self.assertEqual(valids, [False, False, False, False])
        self.top.run()  
        # exec_count should change for all sub comps but comp2
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([2, 1, 2, 2, 2, 2, 2, 2], exec_count)
        outs = [(7,-5),(3,-1),(7,3),(9,5),(6,8),(7,3),(5,1),(12,6)]
        for comp,vals in zip(allcomps,outs):
            self.assertEqual((comp,vals[0],vals[1]), 
                             (comp,self.top.get(comp+'.c'),self.top.get(comp+'.d')))
    
    def test_lazy4(self):
        self.top.run()
        self.top.sub.set('b2', 5)
        self.assertEqual(self.top.sub.get_valid(subvars),
                         [True,False,
                          True,False,
                          True,True,
                          False,True,
                          True,False,
                          False,True,
                          False,False,
                          False,False,
                          True,True,
                          False,False,
                          False,False,
                          False,False])
        self.top.run()
        # exec_count should change for all sub comps but comp3 and comp7 
        self.assertEqual([2, 2, 1, 2, 2, 2, 1, 2], 
                         [self.top.get(x).exec_count for x in allcomps])
        outs = [(2,0),(6,-4),(5,1),(4,0),(1,9),(2,-2),(3,-1),(5,3)]
        for comp,vals in zip(allcomps,outs):
            self.assertEqual((comp,vals[0],vals[1]), 
                             (comp,self.top.get(comp+'.c'),self.top.get(comp+'.d')))
    
    def test_lazy_inside_out(self):
        self.top.run()
        self.top.comp7.b = 4
        # now run sub.comp1 directly to make sure it will force
        # running of all components that supply its inputs
        self.top.sub.comp1.run()
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([2, 1, 2, 1, 2, 1, 2, 1], exec_count)
        outs = [(7,-5),(3,-1),(7,3),(7,3),(6,8),(5,1),(5,-3),(8,6)]
        for comp,vals in zip(allcomps,outs):
            self.assertEqual((comp,vals[0],vals[1]), 
                             (comp,self.top.get(comp+'.c'),self.top.get(comp+'.d')))
            
        # now run comp8 directly, which should force sub.comp4 to run
        self.top.comp8.run()
        exec_count = [self.top.get(x).exec_count for x in allcomps]
        self.assertEqual([2, 1, 2, 2, 2, 1, 2, 2], exec_count)
        outs = [(7,-5),(3,-1),(7,3),(9,5),(6,8),(5,1),(5,-3),(12,6)]
        for comp,vals in zip(allcomps,outs):
            self.assertEqual((comp,vals[0],vals[1]), 
                             (comp,self.top.get(comp+'.c'),self.top.get(comp+'.d')))
            
    def test_sequential(self):
        # verify that if components aren't connected they should execute in the
        # order that they were added to the workflow instead of hash order
        global exec_order
        top = set_as_top(Assembly())
        top.add('c2', Simple())
        top.add('c1', Simple())
        top.add('c3', Simple())
        top.add('c4', Simple())
        top.driver.workflow.add(['c1','c2','c3','c4'])
        top.run()
        self.assertEqual(exec_order, ['c1','c2','c3','c4'])
        top.connect('c4.c', 'c3.a')  # now make c3 depend on c4
        exec_order = []
        top.c4.a = 2  # makes c4 run again
        top.run()
        self.assertEqual(exec_order, ['c4','c3'])
        
        
    def test_expr_deps(self):
        top = set_as_top(Assembly())
        driver1 = top.add('driver1', DumbDriver())
        driver2 = top.add('driver2', DumbDriver())
        top.add('c1', Simple())
        top.add('c2', Simple())
        top.add('c3', Simple())
        
        top.driver.workflow.add(['driver1','driver2','c3'])
        top.driver1.workflow.add('c2')
        top.driver2.workflow.add('c1')
        
        top.connect('c1.c', 'c2.a')
        top.driver1.add_objective("c2.c*c2.d")
        top.driver2.add_objective("c1.c")
        top.run()
        self.assertEqual(exec_order, ['driver2','c1','driver1','c2','c3'])
        

    def test_set_already_connected(self):
        try:
            self.top.sub.comp2.b = 4
        except Exception, err:
            self.assertEqual(str(err), 
                "sub.comp2: 'b' is already connected to source 'parent.b2' and cannot be directly set")
        else:
            self.fail('Exception expected')
        try:
            self.top.set('sub.comp2.b', 4)
        except Exception, err:
            self.assertEqual(str(err), 
                "sub.comp2: 'b' is connected to source 'parent.b2' and cannot be set by source 'None'")
        else:
            self.fail('Exception expected')
            
    def test_force_with_input_updates(self):
        top = set_as_top(Assembly())
        top.add('c2', Simple())
        top.add('c1', Simple())
        top.c2.force_execute = True
        top.connect('c1.c', 'c2.a')
        top.driver.workflow.add(['c1','c2'])
        top.run()
        self.assertEqual(top.c2.a, 3)
        top.c1.a = 2
        top.run()
        self.assertEqual(top.c2.a, 4)

    def test_get_required_compnames(self):
        sub = self.top.sub
        sub.add('driver', DumbDriver())
        sub.driver.add_objective('comp6.c')
        sub.driver.add_objective('comp5.d')
        self.assertEqual(sub.driver._get_required_compnames(),
                         set(['comp6','comp5']))
        sub.driver.add_parameter('comp1.a')
        self.assertEqual(sub.driver._get_required_compnames(),
                         set(['comp6','comp5','comp1','comp4']))
        sub.driver.add_parameter('comp3.a')
        self.assertEqual(sub.driver._get_required_compnames(),
                         set(['comp6','comp5','comp1','comp4','comp3']))

class DependsTestCase2(unittest.TestCase):

    def setUp(self):
        self.top = set_as_top(Assembly())
        self.top.add('c2', Simple())
        self.top.add('c1', Simple())
    
    def test_connected_outs(self):
        self.assertEqual(self.top.c1.list_outputs(connected=True), [])
        self.top.connect('c1.c', 'c2.a')
        self.assertEqual(self.top.c1.list_outputs(connected=True), ['c'])
        self.top.connect('c1.d', 'c2.b')
        self.assertEqual(set(self.top.c1.list_outputs(connected=True)), set(['c', 'd']))
        self.top.disconnect('c1.d', 'c2.b')
        self.assertEqual(self.top.c1.list_outputs(connected=True), ['c'])
        
        
if __name__ == "__main__":
    
    #import cProfile
    #cProfile.run('unittest.main()', 'profout')
    
    #import pstats
    #p = pstats.Stats('profout')
    #p.strip_dirs()
    #p.sort_stats('time')
    #p.print_stats()
    #print '\n\n---------------------\n\n'
    #p.print_callers()
    #print '\n\n---------------------\n\n'
    #p.print_callees()
        
    unittest.main()


