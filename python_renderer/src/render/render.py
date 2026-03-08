import pygame
import time
import sys
import os
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

from enumData.bltype import blType

from src.render.colorsystem import ColorSystem
from datamanager.datamanager import DataManager

from sharedMemoryFileWriter import SharedMemoryWriter


def create_fbo(w, h):
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    fbo = glGenFramebuffers(1)
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D, tex, 0)

    assert glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE
    glBindFramebuffer(GL_FRAMEBUFFER, 0)

    return fbo, tex

class BaseRenderer:
    def __init__(self, bl_type, movement_func, width=1920, height=1080):
        self.display_size = (width, height)
        self.bl_type = bl_type
        self.movement_func = movement_func
        self.session_manager = DataManager()
        self.cs = ColorSystem()
        self.ground_size = 12.0
        self.orbit_radius = 5.0
        self.ball_radius = 1.0
        self.speed = 2.0
        self.edge_margin = 0.85

        self.fbo = None
        self.fbo_tex = None
        self.shm = None
#self.shm = SharedMemoryWriter("frames", 800, 600)  
    def _init_opengl(self):
        try:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            w, h = self.display_size
            aspect = w / h
            # x goes left-right, z goes up-down (top-down camera)
            glOrtho(
                -self.ground_size,          # left
                self.ground_size,           # right
                -self.ground_size / aspect, # bottom
                self.ground_size / aspect,  # top
                0.1, 100.0
            )
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_NORMALIZE)
            self.cs.init_lighting()
        except Exception as e:
            print(f"Error initing scene: {e}")

    def _draw_ground(self, size):
        if self.bl_type == blType.Achromatopsia:
            glColor3f(0.3, 0.3, 0.3)
        else:
            glColor3f(0.2, 0.4, 0.2)
        
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-size, 0, -size)
        glVertex3f(-size, 0, size)
        glVertex3f(size, 0, size)
        glVertex3f(size, 0, -size)
        glEnd()
    
    def _draw_ball(self, position, radius, color):
        glPushMatrix()
        glTranslatef(*position)
        glColor3f(*color)
        quadric = gluNewQuadric()
        gluSphere(quadric, radius, 32, 32)
        gluDeleteQuadric(quadric)
        glPopMatrix()
    
    def _setup_camera(self):
        glLoadIdentity()
        glRotatef(90, 1, 0, 0)
        glTranslatef(0.0, -20.0, 0.0)

class EyeGymnasticsOne(BaseRenderer):
     def run(self):
        session_data = self.session_manager.start_session(
            self.bl_type, 
            self.movement_func.__name__
        )
        try:
            self.shm = SharedMemoryWriter("frames", self.display_size[0], self.display_size[1])            
            pygame.init()
            pygame.display.set_mode(self.display_size, DOUBLEBUF | OPENGL | HIDDEN)
            pygame.display.set_caption(f"Eye Gymnastics - {self.bl_type.name}")
            self._init_opengl()
            self.fbo, self.fbo_tex = create_fbo(*self.display_size)
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
            ball_position = [0, 0, 0]
            start_time = time.time()
            clock = pygame.time.Clock()
            running = True
            
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                
                current_time = time.time() - start_time
                ball_position[0], ball_position[1], ball_position[2] = self.movement_func(
                    current_time, self.orbit_radius, self.ground_size * self.edge_margin, self.speed
                )
                self.session_manager.log_coordinates(ball_position)
                ball_color = self.cs.calc_cur_color(self.bl_type, ball_position, 20.0, current_time)
                
                self.cs.set_background_color(self.bl_type)
                
                glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                self._setup_camera()
                self._draw_ground(20.0)
                self._draw_ball(ball_position, self.ball_radius, ball_color)                
                
                w, h = self.display_size
                raw = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
                img = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                raw = np.flipud(img).tobytes()
                
                # Write to file-based shared memory
                self.   shm.write_frame(raw)          
                time.sleep(0.001)
                clock.tick(60)
            
            session_data["status"] = "completed"

        except KeyboardInterrupt:
            session_data["status"] = "interrupted"
        except Exception as e:
            import traceback
            traceback.print_exc()
            session_data["status"] = "error"
            self.session_manager.add_error(e)
        finally:
            self.session_manager.end_session(session_data)
            pygame.quit()

class EyeGymnasticsTwo(BaseRenderer):
    def run(self):
        session_data = self.session_manager.start_session(
            self.bl_type, self.movement_func.__name__
        )
        try:
            self.shm = SharedMemoryWriter("frames", self.display_size[0], self.display_size[1])           
            pygame.init()
            pygame.display.set_mode(self.display_size, DOUBLEBUF | OPENGL | HIDDEN)
            pygame.display.set_caption(f"Eye Gymnastics - {self.bl_type.name}")
            self._init_opengl()

            self.fbo, self.fbo_tex = create_fbo(*self.display_size)
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

            ball_positions = [[0, 0, 0], [0, 0, 0]]
            start_time = time.time()
            clock = pygame.time.Clock()
            running = True

            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: running = False

                current_time = time.time() - start_time
                pos1 = self.movement_func(current_time, self.orbit_radius, self.ground_size* self.edge_margin, self.speed)
                ball_positions[0] = list(pos1)
                ball_positions[1] = [-pos1[0], pos1[1], pos1[2]]

                ball_colors = [
                    self.cs.calc_cur_color(self.bl_type, ball_positions[0], 20.0, current_time),
                    self.cs.calc_cur_color(self.bl_type, ball_positions[1], 20.0, current_time)
                ]
                self.session_manager.log_coordinates(ball_positions[0])

                self.cs.set_background_color(self.bl_type)
                glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                self._setup_camera()
                self._draw_ground(20.0)
                for pos, color in zip(ball_positions, ball_colors):
                    self._draw_ball(pos, self.ball_radius, color)

                w, h = self.display_size
                raw = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
                img = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
                raw = np.flipud(img).tobytes()

                self.shm.write_frame(raw)
                time.sleep(0.001)
                clock.tick(60)

            session_data["status"] = "completed"

        except KeyboardInterrupt:
            session_data["status"] = "interrupted"
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            traceback.print_exc()
            session_data["status"] = "error"
            self.session_manager.add_error(e)
        finally:
            if self.shm: self.shm.close()
            self.session_manager.end_session(session_data)
            pygame.quit()