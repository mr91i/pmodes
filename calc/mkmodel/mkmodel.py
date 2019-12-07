#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function,	absolute_import, division
import os, copy, pickle, argparse, sys
import numpy	  as np
import pandas	  as pd 
import matplotlib.cm as cm
from scipy import optimize
from collections import OrderedDict as od
dn_here = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
dn_home = os.path.abspath(dn_here + '/../../')
sys.path.append(dn_home)
dn_pkl = dn_home + '/calc/radmc'
print('\nExecute %s:\n'%__file__)
import calc.plotter as mp
from calc import cst 
from calc import CubicSolver

parser = argparse.ArgumentParser(description='This code calculates the kinetic structure based on a model.')
parser.add_argument('-d','--debug',action='store_true')
parser.add_argument('--disk',action='store_true')
parser.add_argument('--norot',action='store_true')
parser.add_argument('--no_param_tuning',action='store_true')
parser.add_argument('-m','--model',choices=['CM','Simple','TSC'],default='CM')
parser.add_argument('--submodel',choices=[None,'CM','Simple','TSC'],default=None)
parser.add_argument('--obj',choices=['L1527','None'],default='L1527') 
parser.add_argument('--cr', type=float)
parser.add_argument('--mass',type=float)
parser.add_argument('--L',type=float)
parser.add_argument('--cavity_angle',type=float,default=None)
parser.add_argument('--pkl_name')
args = parser.parse_args()
if args.obj=='L1527':
   def_cr	= 200
   def_mass = 0.18 #0.18 
   def_L = 2.75
   def_cavity_angle = 45
   def_pkl_name = 'L1527'
else:
   def_cr	= 50
   def_mass = 1.0	
   def_cavity_angle = 0
   def_pkl_name = None
parser.set_defaults(cr=def_cr, 
					mass=def_mass, 
					cavity_angle=def_cavity_angle, 
					L=def_L,
					pkl_name=def_pkl_name)
args = parser.parse_args()

## Global Parameters ##
use_solution_0th = 0
mp.dbg = args.debug
Simple_density = 1
r_in   = 1 *cst.au
r_out  = 1e4 *cst.au
nr	   = 601 
th_in  = 1e-6
th_out = np.pi/2 
nth    = 91
ph_in  = -np.pi
ph_out = np.pi
nph    = 1
t_in   = 5e5 *cst.yr
t_out  = 5e5 *cst.yr
nt	   = 1
#######################
def main():
	r_ax  = np.logspace( np.log10( r_in )  , np.log10( r_out ) , nr	)
	th_ax = np.linspace( th_in	 , th_out , nth	  )
	ph_ax = np.linspace( ph_in	 , ph_out , nph   )
	t_ax  = np.linspace( t_in	 , t_out  , nt	  )
	for t in t_ax:
		Cm = Calc_2d_map( t , r_ax , th_ax	, ph_ax )
		D = Cm.calc()
		Plots( D )

#
# Calculator
#
class Calc_2d_map:
	
	def __init__(self , t , r_ax , th_ax , ph_ax ):
		## Non Variable aramters Through Calculation
		self.t	  = t  
		self.r_ax = r_ax
		self.th_ax = th_ax
		self.ph_ax = ph_ax
		self.mu	  = np.round( np.cos( self.th_ax ) , 15)
		self.sin  = np.where( self.mu==1 , 1e-100 , np.sqrt( 1 - self.mu**2 ) ) #np.sqrt( 1 - self.mu**2 )	
		self.Mfin = 0.7 * cst.Msun
		self.m0 = 0.975
		self.res = {}
		self.Tenv	=	10
		self.cs	= np.sqrt( cst.kB * self.Tenv/cst.mn )
		self.Mdot = self.cs**3*self.m0/cst.G 
		self.M, self.t = self.give_Mass_and_time(self.Mdot, Mstar = args.mass*cst.Msun)
		self.GM = cst.G * self.M
		self.Omg			   = self.give_Omega( self.cs , self.t , self.M , mode='centrifugal_radius', r_CR=args.cr*cst.au)
		self.j0	 = self.Omg * ( self.m0 * self.cs * self.t * 0.5 )**2
		self.Rcb  = self.j0**2 / ( self.GM * 2 ) # 50 * cst.au
		self.Rcr  = self.Rcb*2 # 50 * cst.au
		self.r_in_lim = self.cs*self.Omg**2* self.t**3
		self.req  = self.Rcb * 2 * np.sin( args.cavity_angle/180 * np.pi )**2
		self.Md	= 0.1*self.M
		self.Td	= 30
		self.csd = np.sqrt( cst.kB * self.Td/cst.mn )
		self.cavity_angle = args.cavity_angle
		self.mu_cav = np.cos(args.cavity_angle/180*np.pi)
		self.Rs = cst.Rsun
		print(	args.L,  cst.Lsun )
		self.Ls = args.L * cst.Lsun
		self.Ts = self.Ls**0.25 * cst.Tsun
		self.print_params()	

	def print_params(self):
		print('Parameters:')
		def print_format( name , val , unit):
			print( name.ljust(10) + 'is    {:10.2g}   '.format(val) + unit.ljust(10)	   )
		print_format( 'T' , self.Tenv , 'K' )
		print_format( 'cs' , self.cs/cst.kms , 'km/s' )
		print_format( 't' , self.t/cst.yr , 'yr' )
		print_format( 'M' , self.M/cst.Msun , 'Msun' )
		print_format( 'Omega' , self.Omg , 's^-1' )
		print_format( 'dM/dt' , self.Mdot/(cst.Msun/cst.yr) , 'M/yr' )
		print_format( 'r_lim' , self.r_in_lim/cst.au , 'au' )
		print_format( 'j0' , self.j0/(cst.kms*cst.au)  , 'au*km/s' )
		print_format( 'j0' , self.j0/(cst.kms*cst.pc)  , 'pc*km/s' )
		print_format( 'Rcb' , self.Rcb/cst.au , 'au' )
		print_format( 'Rcr' , self.Rcr/cst.au , 'au' )
		print_format( 'c.a.' , args.cavity_angle , '' )
		print('')

##
	def calc_Kinematics(self, r ,model='CM'):
		if model=='CM':
			solver = self.get_Kinematics_CM
		elif model=='Simple':
			solver = self.get_Kinematics_SimpleBalistic

		rho, ur, uth, uph, zeta, mu0 = solver(r)

		if Simple_density:
			rho = self.get_Kinematics_SimpleBalistic( r )[0]
	
		uR = ur * self.sin + uth * self.mu
		uz = ur * self.mu  - uth * self.sin
		return rho, ur, uth, uph, zeta, mu0, uR, uz

	def get_mu0(self, zeta, solver='roots'):
		def sol1(m):
			return np.roots([zeta, 0 ,1-zeta ,-m]).real 
		def sol2(m):
			return CubicSolver.solve(zeta, 0 , 1-zeta ,-m).real	
		solver = sol2
		root = [None]*len(self.mu)
		for i, m in enumerate(self.mu):
			sol = [ round(a,10) for a in solver(m) if 0<= round(a,10) <=1]	#if m!=0 else [0]
#			if len(sol)>1:
#				print( zeta, m, '{:.16f}'.format(sol[0]))	
			root[i] = sol[0] ## 0 : Choose a solution where gas comes vertically
		return np.array(root)
		
	def get_Kinematics_CM( self, r ):
		zeta =	self.j0**2 / ( self.GM * r	)
		mu0  = self.get_mu0(zeta) 
		sin0 = np.sqrt(1 - mu0**2) 
		v0 = np.sqrt( self.GM / r ) 
		mu_to_mu0 = 1 - zeta*(1 - mu0**2) #np.where( np.logical_and(mu0==0,mu==0) , 1-zeta, mu/mu0 )		
		ur	= - v0 * np.sqrt( 1 + mu_to_mu0 ) 
		uth =	v0 * zeta*sin0**2*mu0/self.sin * np.sqrt( 1 + mu_to_mu0 )
		uph =	v0 * sin0**2/self.sin		  * np.sqrt( zeta )
		rho = - self.Mdot / (4 * np.pi * r**2 * ur) / (1 + zeta*(3*mu0**2-1)	)
		if args.cavity_angle is not None:
			mask = np.where( mu0 < self.mu_cav , 1 , 0	)
		return rho*mask, ur*mask, uth*mask, uph*mask, zeta, mu0	

	def get_Kinematics_SimpleBalistic(self, r, p=-1.5, r0=None, rho0=None, Mdot=None, h=0.1, fillv=0):
		vff = np.sqrt(2 * self.GM / r )
		x = r/self.Rcb
		b_env = np.logical_and( r*self.sin >= self.Rcb, self.mu <= self.mu_cav )
		rho   = np.where( b_env, self.Mdot/(4*np.pi*r**2 *vff ), fillv )
		ur	= - vff * np.sqrt( np.where( b_env, 1-1/x, fillv)	)
		uth = np.where( b_env, 0, fillv)
		uph = np.where( b_env, vff/np.sqrt(x), fillv)
		zeta = 0
		mu0  = self.mu
		return rho, ur, uth, uph, zeta, mu0

	def put_Disk_sph(self, r , CM=False, mode='exponential_cutoff' , ind=-1):
		if not args.disk:
			return np.zeros_like( self.th_ax )
		R = r*self.sin
		z = r*self.mu
		if mode=='CM_visc':
		# Viscous case
			u = R/self.Rcr
#			P = self.Mfin / self.Mdot / ( self.Rcr**2 / (3*0.01*self.csd**2) * np.sqrt(self.GM /self.Rcr_fin**3) )
			P = (3*0.01*self.csd**2) / np.sqrt(self.GM /self.Rcr**3) * self.M**6/self.Mfin**5/self.Mdot/self.Rcr**2
			P_rd2 = 3 * 0.1 * self.Td/self.Tenv * np.sqrt(self.Mfin/self.M) * np.sqrt(cst.G * self.Mfin/self.Rcr)/self.cs
			a3 = 0.2757347731 # (2^10/3^11)^(0.25)
			ue = np.sqrt(3*P)*(1-56/51*a3/P**0.25)
			y  = np.where(u < 1, 2*np.sqrt(1-u) + 4/3/np.sqrt(u)*(1-(1+0.5*u)*np.sqrt(1-u) )	 , 4/3/np.sqrt(u)  )	
			y  = np.where(u <= ue, y - 4/3/np.sqrt(ue) , 0 )
			Sigma = 0.5/P * y * self.M/(np.pi*self.Rcr**2)		
			print(P,P_rd2)
		elif mode=='S+94':
			pass	
#			A = 4*a/(m0 * Omg0 * cst.Rsun)
#			u = R/R_CR
#			V = 
#			Sigma = (1-u)**0.5 /(2*A*u*t**2*V)
			
		elif mode=='exponential_cutoff':
			Sigma_0 = self.Md/(2*np.pi*self.Rcr**2)/(1-2/np.e)
			Sigma = Sigma_0 * (R/cst.au)**ind  * np.exp( -(R/self.Rcr)**(2+ind) )
		elif mode=='tapered_cutoff':
			Sigma_0 = self.Md/(2*np.pi*R_**2) * (ind+3)
			Sigma = self.Md/(2*np.pi) * (ind+3)*self.Rcr**(-ind-3)	* (R/cst.au)**ind
		H  = np.sqrt( cst.kB * self.Td / cst.mn ) / np.sqrt(cst.G*self.M/R**3)
		rho = Sigma/np.sqrt(2*np.pi)/H * np.exp( - 0.5*z**2/H**2	)
		return rho


	def calc(self):
		#
		# Set parameters
		#
		vals_rt = {}
		vals_prt = {}
		#	
		# Main loop in r-axis
		#
		for ph in self.ph_ax:
			for r in self.r_ax:
				R_ax, z_ax	= r*self.sin , r*self.mu
				rho, ur, uth, uph, zeta, mu0, uR, uz = self.calc_Kinematics( r , model=args.model )
				rho_disk = self.put_Disk_sph( r , mode='CM_visc')	
				b_disk = rho_disk > np.nan_to_num(rho)
				v_Kep	 = np.sqrt(self.GM / R_ax )

				vals = {  'R':R_ax, 'z': z_ax, 'den':rho,
							'ur':ur,'uph':uph,'uth':uth,'uR':uR,'uz':uz ,
							'rr':np.full_like(self.th_ax , r) , 
							'tt': self.th_ax ,
							'zeta':zeta, 
							'mu0':mu0 ,
							'den_tot':rho + rho_disk,  
							'vr_tot':np.where( b_disk	, 0	   , ur  ), 
							'vphi_tot':np.where( b_disk	, v_Kep , uph ), 
							'vth_tot':np.where( b_disk	, 0	   , uth )	
						}  
	
				if args.submodel is not None:
					rho_sub, ur_sub, uth_sub, uph_sub, zeta_sub, mu0_sub, uR_sub, uz_sub = self.calc_Kinematics( r , model=args.submodel)
					vals.update({'den_sub':rho_sub, 'ur_sub':ur_sub,'uph_sub':uph_sub,'uth_sub':uth_sub,'uR_sub':uR_sub,'uz_sub':uz_sub }  )
		
				# Accumurate list to res 
				# Stack: stacked_value = stack( vals )
				# [ r1:[ t1 t2 ... tn  ], ... rn:[	]  ]
				self.stack( vals, vals_rt	)
			self.stack( vals_rt , vals_prt	)

		# Convert stacked values to ndarray and add to "self" class
		for k,v_prt in vals_prt.items():
			setattr( self, k, np.array(v_prt).transpose(1,2,0)	 )

		# Save to pickle
		self.Save_pickle() 
		print(self.__module__,self.__init__)
		for x in dir(self):
			print( x, ':', type(eval("self."+x) ) )

		return self

	def Save_pickle(self):
		stamp = '{:.0e}'.format( self.t/cst.yr ) if args.pkl_name == 'time' else args.pkl_name
		savefile = '%s/res_%s.pkl'%(dn_pkl, stamp)
		pd.to_pickle( class_to_dict(self) , savefile)
		print('Saved : %s\n'%savefile )	

	def class_to_dict(cls):
		print(cls.__dict__)
		return cls.__dict__	


	def give_Mass_and_time(self, t=None, Mstar=None):
		if args.no_param_tuning :
			return self.Mdot * t , t
		else: 
			return Mstar , Mstar / self.Mdot
		
	def give_Omega(self, cs, t, M , mode='const', v_CR=None , r_CR=None):
		if args.norot:
			return 0
		r_col = self.m0*0.5*cs*t
		if mode=='const':
			return 1e-14
		if mode=='velocity_peak':
			## v_CR = velocity peak
			##		= sqrt(2) * GM / l
			## l  = (0.5*cs*t)**2 * Omega
			## --> Omega = sqrt(2) * GM / vpeak / (0.5*cs*t)**2 
			return sqrt(2) * self.GM / v_CR / r_col**2
		if mode=='centrifugal_radius':
			## r_CR = given
			##		= l**2 /(GM)
			##	l  = (0.5*cs*t)**2 * Omega
			return np.sqrt( self.GM * r_CR )/r_col**2


	def stack(self, dict_vals, dict_stacked ):
		for k, v in dict_vals.items():
			if not k in dict_stacked:
				dict_stacked[k] = []
			if not isinstance(v,(list,np.ndarray)):
				v=[v]
			dict_stacked[k].append( v )
		dict_vals.clear()

#
# Plotter
#
def Plots( D , r_lim=500):

	def slice_at_midplane( tt, *vals_rtp):
		iphi=0
		if len(vals_rtp) >= 2:
			return np.array( [	val_rtp.take(iphi,2)[ tt.take(iphi,2)==np.pi/2 ] for val_rtp in vals_rtp	  ]	 )
		else:
			return	vals_rtp.take(iphi,2)[ tt==np.pi/2 ]

	####

	tstamp = args.pkl_name if args.pkl_name else '{:.0e}'.format(D.t/cst.yr)
	ph_ax = D.ph_ax if nph!=1 else np.linspace(-np.pi,np.pi,31	)
	r_mg , th_mg , ph_mg =	np.meshgrid( D.r_ax , D.th_ax , ph_ax , indexing='ij' )
	R_mg , z_mg  = r_mg * [ np.sin( th_mg ) ,  np.cos( th_mg ) ]
	x_mg , y_mg =  R_mg * [ np.cos(ph_mg)	, np.sin(ph_mg) ]

	def draw_map( v , name , rang , log=True, V=None, cbl=None,  **kwargs):
		mp.map( R_mg.take(0,2)/cst.au , z_mg.take(0,2)/cst.au , v.take(0,2)	, 'map_{}_{}'.format(name,tstamp), 
					xl='Radius [au]' , yl='Height [au]', cbl=cbl,
					logx=False, logy=False, logcb=log, leg=False, 
					xlim=[0,r_lim], ylim=[0,r_lim], cblim=rang, **kwargs )

	def draw_plane_map( v , name , rang , log=True, V=None, cbl=None, **kwargs):
		if v.shape[2]==1:
			v = np.concatenate([v]*31,axis=2)
		mp.map( x_mg.take(-1,1)/cst.au , y_mg.take(-1,1)/cst.au , v.take(-1,1) , 'plmap_{}_{}'.format(name,tstamp),
					xl='Radius [au]' , yl='Height [au]', cbl=cbl,
					logx=False, logy=False, logcb=log, leg=False,
					xlim=[-1000,1000], ylim=[-1000,1000], cblim=rang,seeds_angle=[0,2*np.pi], **kwargs )		

	# Density and velocity map
	Vec = np.array( [ D.uR.take(0,2) , D.uz.take(0,2) ] )
	draw_map( D.den, 'den', [1e-21, 1e-16] , cbl=r'log Density [g/cm$^{3}$]', div=10, Vector=Vec,n_sl=40)

	# Ratio between mu0 and mu : where these gas come from
	draw_map( D.mu0/np.cos( D.tt ), 'mu0_mu',[0, 10] , cbl=r'$\mu_{0}/\mu$', div=10, Vector=Vec,n_sl=40,log=False)

	## Analyze radial profiles at the midplane
	# Slicing 
	V_LS = x_mg/r_mg * D.uph - y_mg/r_mg*D.ur
	ux = D.ur *np.cos(ph_mg) - D.uph*np.sin(ph_mg)
	uy = D.ur *np.sin(ph_mg) + D.uph*np.cos(ph_mg)
	# dV/dy = dV/dr * dr/dy + dV/dth * dth/dy
	#		= dV/dr * 1/sin + dV/dth * 1/r*cos
	#dVdy = V_LS/y_mg #np.gradient( V_LS, D.r_ax, axis = 0 )/np.sin(ph_mg) + np.gradient( V_LS, D.ph_ax , axis = 2)/x_mg
	Vec = np.array( [ ux.take(-1,1) , uy.take(-1,1) ] )
	draw_plane_map( V_LS/1e5, 'Vls', [-2.0, 2.0] , cbl=r'V_LS [km s$^{-1}$]', div=20, n_sl=40, log=False, cmap=cm.get_cmap('seismic'),Vector=Vec)
	draw_plane_map( D.den, 'den', [1e-18,1e-16] , cbl=r'log Density [g/cm$^{3}$]', div=4, n_sl=40)

	den0, uR0 , uph0, den_tot0	= slice_at_midplane( th_mg , D.den , D.uR , D.uph , D.den_tot )  

	mp.set( x = D.r_ax/cst.au , xlim=[0,500] )
	# Density as a function of distance from the center
	mp.plot( [['nH2_env',den0/cst.mn], ['nH2_disk',(den_tot0-den0)/cst.mn], ['nH2_tot',den_tot0/cst.mn]]	,
				'dens_%s'%tstamp , ylim=[1e4,1e15] ,  xlim=[1,1000] ,
				lw=[3,3,6], c=[None,None,'k'], ls=['--',':','-'], 
				loglog=True, vl=[ 2*D.Rcb/cst.au ])

	# Make a 'balistic' orbit similar procedure to Oya+2014
	mp.plot( [[	'-uR',-uR0/cst.kms] ,['uph',uph0/cst.kms ]]	,
				'v_%s'%tstamp  , ylim=[-1,3] ,	xlim=[0,500] , 
				lw=[ 2,2,4,4], ls=['-','-','--','--'])

	mp.plot( [[	'-uR',-uR0/max(uph0) ],['uph',uph0/max(uph0) ]] ,
				'vnorm_%s'%tstamp  , ylim=[0,1.5] ,	x=D.r_ax/D.Rcb, xlim=[0,3] , 
				lw=[ 2,2,4,4], ls=['-','-','--','--'])

	if args.submodel is not None:
		# see when and how much the results is different
		den0_TSC, uR0_TSC , uph0_TSC = slice_at_midplane( re, th_mg , 'den_sub' , 'uR_sub' , 'uph_sub' )
		mp.plot( { 'log nH2 - 6':np.log10(den0/cst.mn) -6, 
					'-uR':-uR0/cst.kms , 
					'uph':uph0/cst.kms ,	
					'log nH2_TSC - 6':np.log10(den0_sub/cst.mn) -6,
					'-uR_TSC':-uR0_sub/cst.kms , 
					'uph_TSC':uph0_sub/cst.kms }	, 
					'vden_compare_%s'%tstamp	  , x = D.r_ax/cst.au ,xlim=[0,500],ylim=[-2,10] , 
					lw=[ 3, 3,3,6,6,6], c=['k', ], ls=['-','-','-','--','--','--'], 
					vl=[D.Rcb*2/cst.au, D.r_in_lim/cst.au])
	return 

##########################################################################################################################

###########
if __name__ == '__main__':
	main()
###########

