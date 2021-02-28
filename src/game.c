#include "game.h"
#include "bob_new.h"
#include <ace/managers/copper.h>
#include <ace/managers/log.h>
#include <ace/managers/mouse.h>
#include <ace/types.h>
#include <ace/managers/viewport/camera.h>
#include <ace/utils/bitmap.h>
#include <ace/utils/custom.h>
#include <ace/utils/extview.h>
#include <ace/utils/file.h>
#include <ace/utils/palette.h>
#include <ace/managers/key.h>
#include <ace/managers/game.h>
#include <ace/managers/system.h>
#include <ace/managers/viewport/simplebuffer.h>
#include <ace/managers/viewport/scrollbuffer.h>
#include <ace/managers/viewport/tilebuffer.h>
#include <ace/managers/blit.h>
#include <stdint.h>


#define TILE_SHIFT 4
#define TILE_SIZE 1 << TILE_SHIFT
#define MAP_SIZE 64

#define BPP 5
#define COLORS 1 << BPP

static tView *s_pView; // View containing all the viewports
static tVPort *s_pVpPanel; // Viewport for panel
static tSimpleBufferManager *s_pPanelBuffer;
static tVPort *s_pVpMain; // Viewport for playfield
static tTileBufferManager *s_pMapBuffer;
static tCameraManager *s_pMainCamera;
static tBitMap *s_pMapBitmap;

static tBitMap *s_pGoldMineBitmap;
static tBitMap *s_pGoldMineMask;
static tBobNew s_GoldMineBob;

// palette switching
static uint16_t s_pMapPalette[COLORS];
static uint16_t s_pPanelPalette[COLORS];
static tCopBlock *s_pPaletteBlocks[2];

#define MAP_HEIGHT 200
#define PANEL_HEIGHT 48

/*
 * void myTileDrawCallback(UWORD uwTileX, UWORD uwTileY,
 *                         tBitMap *pBitMap, UWORD uwBitMapX, UWORD uwBitMapY) {
 *     _logWrite("Drawing tile %d:%d\n", uwTileX, uwTileY);
 * }
 */

void gameGsCreate(void) {
    logWrite("load view 0\n");
    viewLoad(0);
    logWrite("system use\n");

    logWrite("Create view\n");
    s_pView = viewCreate(0,
                         TAG_VIEW_GLOBAL_CLUT, 1,
                         TAG_VIEW_COPLIST_MODE, VIEW_COPLIST_MODE_BLOCK,
                         TAG_DONE);

    logWrite("Create map\n");

    s_pGoldMineBitmap = bitmapCreateFromFile("resources/forest_tileset/graphics/tilesets/forest/neutral/buildings/gold_mine.bm", 0);
    s_pGoldMineMask = bitmapCreateFromFile("resources/forest_tileset/graphics/tilesets/forest/neutral/buildings/gold_mine_mask.bm", 0);

    // create map area
    paletteLoad("resources/forest_tileset.plt", s_pMapPalette, COLORS);
    s_pPaletteBlocks[0] = copBlockCreate(s_pView->pCopList, COLORS, 0, 0);
    for (uint8_t i = 0; i < COLORS; i++) {
        copMove(s_pView->pCopList, s_pPaletteBlocks[0], &g_pCustom->color[i], s_pMapPalette[i]);
    }

    s_pVpMain = vPortCreate(0,
                            TAG_VPORT_VIEW, s_pView,
                            TAG_VPORT_BPP, BPP,
                            TAG_VPORT_HEIGHT, MAP_HEIGHT,
                            TAG_END);
    for (uint8_t i = 0; i < COLORS; i++) {
        s_pVpMain->pPalette[i] = s_pMapPalette[i];
    }
    s_pMapBitmap = bitmapCreateFromFile("resources/forest_tileset/graphics/tilesets/forest/terrain.bm", 0);
    logWrite("Create tilebuffer\n");
    s_pMapBuffer = tileBufferCreate(0,
                                    TAG_TILEBUFFER_VPORT, s_pVpMain,
                                    TAG_TILEBUFFER_BITMAP_FLAGS, BMF_CLEAR,
                                    TAG_TILEBUFFER_BOUND_TILE_X, MAP_SIZE,
                                    TAG_TILEBUFFER_BOUND_TILE_Y, MAP_SIZE,
                                    TAG_TILEBUFFER_TILE_SHIFT, TILE_SHIFT,
                                    TAG_TILEBUFFER_TILESET, s_pMapBitmap,
                                    TAG_TILEBUFFER_IS_DBLBUF, 0,
                                    TAG_TILEBUFFER_REDRAW_QUEUE_LENGTH, 9,
                                    TAG_END);
    s_pMainCamera = s_pMapBuffer->pCamera;
    logWrite("set camera coords\n");
    cameraSetCoord(s_pMainCamera, 0, 0);

    bobNewManagerCreate(s_pMapBuffer->pScroll->pFront, s_pMapBuffer->pScroll->pBack, s_pMapBuffer->pScroll->uwBmAvailHeight);
    bobNewInit(&s_GoldMineBob, 64, 64, 0, s_pGoldMineBitmap, s_pGoldMineMask, 80, 80);
    bobNewReallocateBgBuffers();

    logWrite("file tile data\n");
    tFile *map = fileOpen("resources/maps/orc12.map", "r");
    for (int x = 0; x < MAP_SIZE; x++) {
        fileRead(map, s_pMapBuffer->pTileData[x], MAP_SIZE);
    }
    fileClose(map);

    logWrite("redraw all\n");
    tileBufferRedrawAll(s_pMapBuffer);

    // create panel area
    paletteLoad("resources/human_panel.plt", s_pPanelPalette, COLORS);
    s_pPaletteBlocks[1] = copBlockCreate(s_pView->pCopList, COLORS, 0, MAP_HEIGHT + 45);
    for (uint8_t i = 0; i < COLORS; i++) {
        copMove(s_pView->pCopList, s_pPaletteBlocks[1], &g_pCustom->color[i], s_pPanelPalette[i]);
    }
    
    s_pVpPanel = vPortCreate(0,
                             TAG_VPORT_VIEW, s_pView,
                             TAG_VPORT_BPP, BPP,
                             // TAG_VPORT_OFFSET_TOP, 1,
                             TAG_VPORT_HEIGHT, PANEL_HEIGHT,
                             TAG_END);
    logWrite("create panel buffer\n");
    s_pPanelBuffer = simpleBufferCreate(0,
                                        TAG_SIMPLEBUFFER_VPORT, s_pVpPanel,
                                        TAG_SIMPLEBUFFER_BITMAP_FLAGS, BMF_CLEAR,
                                        TAG_END);
    bitmapLoadFromFile(s_pPanelBuffer->pFront, "resources/human_panel/graphics/ui/human/panel_2.bm", 48, 0);

    // finish up
    logWrite("load view\n");
    viewLoad(s_pView);
    logWrite("unuse system\n");
    systemUnuse();
}

static uint16_t GameCycle = 0;

void gameGsLoop(void) {
    switch (GameCycle % 1) {
    case 0:
        // This will loop every frame
        if (keyCheck(KEY_W)) {
            cameraMoveBy(s_pMainCamera, 0, -1);
        }
        if (keyCheck(KEY_S)) {
            cameraMoveBy(s_pMainCamera, 0, 1);
        }
        if (keyCheck(KEY_A)) {
            cameraMoveBy(s_pMainCamera, -1, 0);
        }
        if (keyCheck(KEY_D)) {
            cameraMoveBy(s_pMainCamera, 1, 0);
        }
        if (keyCheck(KEY_ESCAPE)) {
            gameExit();
        }
        if (keyCheck(KEY_C)) {
            copDumpBlocks();
        }
        if (mouseGetX(MOUSE_PORT_1) > s_pVpMain->uwWidth - 5) {
            cameraMoveBy(s_pMainCamera, 1, 0);
        } else if (mouseGetX(MOUSE_PORT_1) < 5) {
            cameraMoveBy(s_pMainCamera, -1, 0);
        } else if (mouseGetY(MOUSE_PORT_1) < 5) {
            cameraMoveBy(s_pMainCamera, 0, -1);
        } else if (mouseGetY(MOUSE_PORT_1) > s_pVpMain->uwHeight - 5) {
            cameraMoveBy(s_pMainCamera, 0, 1);
        }
    }

    bobNewBegin(s_pMapBuffer->pScroll->pBack);
    if (tileBufferIsTileOnBuffer(s_pMapBuffer, 80 / 16, 80 / 16)) {
        bobNewPush(&s_GoldMineBob);
    }
    bobNewPushingDone();
    bobNewProcessNext();
    bobNewEnd();

    viewProcessManagers(s_pView);
    copProcessBlocks();
    vPortWaitForEnd(s_pVpPanel);
    GameCycle++;
}

void gameGsDestroy(void) {
    systemUse();

    // This will also destroy all associated viewports and viewport managers
    bobNewManagerDestroy();
    viewDestroy(s_pView);
}
