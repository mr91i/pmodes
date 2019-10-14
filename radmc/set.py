#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Import libraries
#
import numpy as np
import pandas as pd
#import cst as cst
import natconst as cst
import pickle
from scipy.interpolate import interp2d

mode={'tgas':0,'line':1}

#from mpl_toolkits.mplot3d import axes3d
#from matplotlib import pyplot as plt

def convert_cyl_to_sph( v_cyl , R_ori , z_ori , RR , zz):
	if 1:
		print( np.log10( R_ori[1:] ) , np.log10( z_ori[1:] ) , np.log10( v_cyl[1:,1:] )		)
		f = interp2d( np.log10( R_ori[1:] ) , np.log10( z_ori[1:] ) , np.log10( v_cyl[1:,1:] )	)
		fv = np.vectorize(f)
		v_sph = 10**fv(  np.log10( RR ) ,  np.log10( zz ) )
	else:
		f = interp2d( R_ori , z_ori , v_cyl )
		fv = np.vectorize(f)
		v_sph = fv( RR , zz)
#	print(zz,np.log10(zz))
	return v_sph

def interpolator( x_ori , y_ori , x_new, y_new ,logx=False ):
	if logx:
		x_ori = np.log10(x_ori) 
#		x2_ori = np.log10(x2_ori)
		x_new = np.log10(x_new)
#		x2_new = np.log10(x2_new)
	def func(v):
		f = interp2d( x_ori , y_ori , v.T  )
		fv = np.vectorize(f)
		return fv( x_new  , y_new )
	if logx :
		return lambda x: 10**func( np.log10(x) )
	else:
		return lambda x: func(x)


#def Produce_Calculate_Parameter():


#class Params():
	# Given parameters
	# Mass of central star , not including disk and envelope
#	self.M = 1 
#	self.T = 1
	# Model parameter
#	self.R = 1
	# Dependent parameters
#	self.L = 1 # StellarEvolution(R)
#	self.age = 1 # StellarEvolution(M,L)

def perform_PMODES():
	os.system( "python3 ../EnDisk_2D.py -o output.pkl" )
		
def main():
	nphot	 = 100000
	
	#
	# Grid parameters
	#
	nr		 = 256 #128
	ntheta	 = 128
#	ntheta	 = 64
	nphi	 = 1
	rin		 = 1*cst.au
	rout	 = 10000*cst.au
	thetaup  = 0 / 180 * np.pi 
#	thetaup  = np.pi*0.5 - 0.7e0
	#
	# Disk parameters
	#
	#
	# Star parameters
	#
	mstar	 = cst.ms
	rstar	 = cst.rs
	tstar	 = cst.ts
	pstar	 = np.array([0.,0.,0.])
	#
	# Make the coordinates
	#
	ri	 = np.logspace(np.log10(rin),np.log10(rout),nr+1)
	thetai	 = np.linspace(thetaup,0.5e0*np.pi,ntheta+1)
	phii	 = np.linspace(0.e0,np.pi*2.e0,nphi+1)
	rc	 = 0.5 * ( ri[0:nr] + ri[1:nr+1] )
	thetac	 = 0.5 * ( thetai[0:ntheta] + thetai[1:ntheta+1] )
	phic	 = 0.5 * ( phii[0:nphi] + phii[1:nphi+1] )
	#
	# Make the grid
	#
	qq		 = np.meshgrid(rc,thetac,phic,indexing='ij')
	rr		 = qq[0]
	tt		 = qq[1]
	RR		 = qq[0]*np.sin( tt )
	zz		 = qq[0]*np.cos( tt )
	
	#
#	 D = pd.read_pickle("res_5e+05_nocav.pkl")
	D = pd.read_pickle("res_1e+05.pkl")
#	D = pd.read_pickle("res_5e+05.pkl")


#	rhog = convert_cyl_to_sph( D["den"] , D["r_ax"] , D["z_ax"] , RR , zz)

#	print(D["r_ax"])

	interp = interpolator(	D["r_ax"] , D["th_ax"]	, rr, tt , logx=True)
	rhog = interp( D["den"]  )

#	print( D["den"] , rhog )
#	exit(1)

	rhod = rhog * 0.01
	vr	= interp( -D["ur"])
	vth =  interp(	D["uth"])
	vph =  interp( D["uph"])

	

#	print(rhog)
#	exit(1)

	#
	# Make a simple solid-body rotating gas flow
	#
	
#	tgas	= np.zeros((nr,ntheta,nphi)) + 280*(rr/cst.au)**(-0.5)
#	vcir	= rrcyl * omega
#	vx		=  vcir * yy / ( rrcyl + 1e-10*sizex )
#	vy		= -vcir * xx / ( rrcyl + 1e-10*sizey )
#	vz		= np.zeros((nx,ny,nz))

	vturb	= np.zeros((nr,ntheta,nphi)) 
	
	#
	# Write the wavelength_micron.inp file
	#
	
	# ALMA Band 6
	if 0:
#		lam1	 = 1.421e3
#		lam2	 = 1.090e3
		lam1	 = 0.1e0
		lam2	 = 7.0e0
		n12		 = 5
		lam12	 = np.logspace(np.log10(lam1),np.log10(lam2),n12)
		lam		 = lam12
		nlam	 = lam.size
	else:
		lam1	 = 0.1e0
		lam2	 = 7.0e0
		lam3	 = 25.e0
		lam4	 = 1.0e4
		n12		 = 20
		n23		 = 100
		n34		 = 30
		lam12	 = np.logspace(np.log10(lam1),np.log10(lam2),n12,endpoint=False)
		lam23	 = np.logspace(np.log10(lam2),np.log10(lam3),n23,endpoint=False)
		lam34	 = np.logspace(np.log10(lam3),np.log10(lam4),n34,endpoint=True)
		lam		 = np.concatenate([lam12,lam23,lam34])
		nlam	 = lam.size
#	
	#
	# Write the wavelength file
	#
	with open('wavelength_micron.inp','w+') as f:
		f.write('%d\n'%(nlam))
		for value in lam:
			f.write('%13.6e\n'%(value))


	#
	# Write the stars.inp file
	#
	with open('stars.inp','w+') as f:
		f.write('2\n')
		f.write('1 %d\n\n'%(nlam))
		f.write('%13.6e %13.6e %13.6e %13.6e %13.6e\n\n'%(rstar,mstar,pstar[0],pstar[1],pstar[2]))
		for value in lam:
			f.write('%13.6e\n'%(value))
		f.write('\n%13.6e\n'%(-tstar))


	#
	# Write the grid file
	#
	with open('amr_grid.inp','w+') as f:
		f.write('1\n')						 # iformat
		f.write('0\n')						 # AMR grid style  (0=regular grid, no AMR)
		f.write('100\n')					 # Coordinate system: spherical
		f.write('0\n')						 # gridinfo
		f.write('1 1 0\n')					 # Include r,theta coordinates
		f.write('%d %d %d\n'%(nr,ntheta,1))  # Size of grid
		for value in ri:
			f.write('%13.6e\n'%(value))		 # X coordinates (cell walls)
		for value in thetai:
			f.write('%13.6e\n'%(value))		 # Y coordinates (cell walls)
		for value in phii:
			f.write('%13.6e\n'%(value))		 # Z coordinates (cell walls)
	



	if mode["line"]:
		mol_name = "c18o"	
		abun_mol = 3e-7 ## c18o
		#
		# Write the molecule number density file. 
		#	
		n_mol  = rhog * abun_mol/(2.34*cst.mp)
		with open('numberdens_%s.inp'%(mol_name),'w+') as f:
			f.write('1\n')						 # Format number
			f.write('%d\n'%(nr*ntheta*nphi))			 # Nr of cells
			data = n_mol.ravel(order='F')			 # Create a 1-D view, fortran-style indexing
			data.tofile(f, sep='\n', format="%13.6e")
			f.write('\n')
	
	
		#
		# Write the lines.inp control file
		#
		with open('lines.inp','w') as f:
			f.write('2\n')# 
			f.write('1\n')# number of molecules
			f.write('%s	 leiden	0 0 0\n'%(mol_name)) # molname1 inpstyle1 iduma1 idumb1 ncol1
	

		#
		# Write the gas velocity field
		#
		with open('gas_velocity.inp','w+') as f:
			f.write('1\n')						 # Format number
			f.write('%d\n'%(nr*ntheta*nphi))			 # Nr of cells
			for ip in range(nphi):
				for it in range(ntheta):
					for ir in range(nr):
						f.write('%13.6e %13.6e %13.6e\n'%(vr[ir,it,ip],vth[ir,it,ip],vph[ir,it,ip]))
	
	
		#
		# Write the microturbulence file
		#
		with open('microturbulence.inp','w+') as f:
			f.write('1\n')						 # Format number
			f.write('%d\n'%(nr*ntheta*nphi))			 # Nr of cells
			data = vturb.ravel(order='F')		   # Create a 1-D view, fortran-style indexing
			data.tofile(f, sep='\n', format="%13.6e")
			f.write('\n')
	
	
		#
		# Write the gas temperature
		#
		if mode["tgas"]:
			with open('gas_temperature.inp','w+') as f:
				f.write('1\n')						 # Format number
				f.write('%d\n'%(nr*ntheta*nphi))			 # Nr of cells
				data = tgas.ravel(order='F')		  # Create a 1-D view, fortran-style indexing
				data.tofile(f, sep='\n', format="%13.6e")
				f.write('\n')


	#
	# Write the dust temperature file
	# NOTE: You can also remove this, and compute the dust
	#		temperature self-consistently with the shell 
	#		command "radmc3d mctherm". Here, however, we 
	#		simply make a guess and write it to file, so
	#		that you can immediately make the images.
	#
	with open('dust_temperature.dat','w+') as f:
		f.write('1\n')						 # Format number


	#
	# Write the density file
	#
	with open('dust_density.inp','w+') as f:
		f.write('1\n')						 # Format number
		f.write('%d\n'%(nr*ntheta*nphi))	 # Nr of cells
		f.write('1\n')						 # Nr of dust species
		data = rhod.ravel(order='F')		 # Create a 1-D view, fortran-style indexing
		data.tofile(f, sep='\n', format="%13.6e")
		f.write('\n')


	#
	# Dust opacity control file
	#
	with open('dustopac.inp','w+') as f:
		opacs = ['silicate']
		f.write('2				 Format number of this file\n')
		f.write('{}				 Nr of dust species\n'.format( len(opacs) ))
		f.write('============================================================================\n')
		for op in opacs:
			f.write('1				 Way in which this dust species is read\n')
			f.write('0				 0=Thermal grain\n')
			f.write('{}		 Extension of name of dustkappa_***.inp file\n'.format( op ))
			f.write('----------------------------------------------------------------------------\n')


	#
	# Write the radmc3d.inp control file
	#
	with open('radmc3d.inp','w+') as f:
		f.write('nphot = %d\n'%(nphot))
#		f.write('scattering_mode_max = 1\n')
		f.write('scattering_mode_max = 0\n')
		f.write('iranfreqmode = 1\n')
		f.write('mc_scat_maxtauabs = 5.d0\n')
		f.write('tgas_eq_tdust = 1')
	del f
		
	pkl = {'rr':rr,'tt':tt,'rhod':rhod}
	pd.to_pickle(pkl, __file__+".pkl",protocol=2)
	
if __name__=='__main__':
	main()
