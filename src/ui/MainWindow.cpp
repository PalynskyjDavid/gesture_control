#include "MainWindow.h"
#include "SettingsDialog.h"

#include <QWidget>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QStatusBar>
#include <QSplitter>
#include <QListWidget>
#include <QComboBox>
#include <QPushButton>
#include <QLabel>
#include <QCheckBox>
#include <QAction>
#include <QGuiApplication>
#include <QScreen>

// -------------------------------
// Constructor
// -------------------------------
MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setupUi();
    loadDefaultGestures();
}

// ---------------------------------------
// Called after dependencies are injected
// ---------------------------------------
void MainWindow::initialize()
{
    if (!gestureEngine_)
    {
        qWarning() << "[MW] ERROR: gestureEngine_ not set before initialize()!";
        return;
    }

    // Now safe to connect
    connect(gestureEngine_, &GestureEngine::handsUpdated,
            this, &MainWindow::onHandsUpdated);

    connect(gestureEngine_, &GestureEngine::connectionStatusChanged,
            this, &MainWindow::onConnectionStatusChanged);

    // local UI connections
    connect(gestureList_, &QListWidget::itemClicked,
            this, &MainWindow::onGestureSelected);

    connect(actionCombo_, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &MainWindow::onBindActionChanged);

    connect(testButton_, &QPushButton::clicked,
            this, &MainWindow::onTestActionClicked);

    connect(trackingCheckBox_, &QCheckBox::toggled,
            this, &MainWindow::onTrackingToggled);

    qDebug() << "[MW] initialize(): connections established.";
}

// ---------------------------------------
// GestureEngine setter with safety
// ---------------------------------------
void MainWindow::setGestureEngine(GestureEngine *eng)
{
    gestureEngine_ = eng;
}

void MainWindow::setupUi()
{
    auto *central = new QWidget(this);
    auto *mainLayout = new QHBoxLayout(central);

    auto *gestureGroup = new QGroupBox(tr("Gestures (per hand)"), central);
    auto *gestureLayout = new QVBoxLayout(gestureGroup);

    gestureList_ = new QListWidget(gestureGroup);
    gestureLayout->addWidget(gestureList_);

    auto *bindGroup = new QGroupBox(tr("Binding / Actions"), central);
    auto *bindLayout = new QVBoxLayout(bindGroup);

    gestureLabel_ = new QLabel(tr("Selected: (none)"), bindGroup);

        auto *settingsAct = new QAction(tr("Gesture Settings..."), this);
    menuBar()->addAction(settingsAct);
    connect(settingsAct, &QAction::triggered, this, &MainWindow::openSettingsDialog);

    actionCombo_ = new QComboBox(bindGroup);
    actionCombo_->addItem("None");
    actionCombo_->addItem("Move mouse (demo)");
    actionCombo_->addItem("Left click");
    actionCombo_->addItem("Right click");
    actionCombo_->addItem("Double click");
    actionCombo_->addItem("Scroll up");
    actionCombo_->addItem("Scroll down");

    testButton_ = new QPushButton(tr("Test action"), bindGroup);
    trackingCheckBox_ = new QCheckBox(tr("Enable tracking (connect to Python)"), bindGroup);

    bindLayout->addWidget(gestureLabel_);
    bindLayout->addWidget(new QLabel(tr("Action for this hand+gesture:"), bindGroup));
    bindLayout->addWidget(actionCombo_);
    bindLayout->addWidget(testButton_);
    bindLayout->addWidget(trackingCheckBox_);
    bindLayout->addStretch();

    auto *splitter = new QSplitter(Qt::Horizontal, central);
    splitter->addWidget(gestureGroup);
    splitter->addWidget(bindGroup);
    splitter->setStretchFactor(0, 1);
    splitter->setStretchFactor(1, 2);

    mainLayout->addWidget(splitter);
    setCentralWidget(central);

    statusLabel_ = new QLabel(tr("Ready"), this);
    statusBar()->addWidget(statusLabel_);

    setWindowTitle(tr("Gesture Control (per-hand)"));
    resize(900, 550);
}

QString MainWindow::makeBindingKey(const QString &hand,
                                   const QString &gesture) const
{
    return hand + ":" + gesture;
}

void MainWindow::loadDefaultGestures()
{
    const QStringList hands = {"Left", "Right"};
    const QStringList gestures = {
        "open_palm",
        "fist",
        "pinch",
        "swipe_left",
        "swipe_right"};

    for (const auto &hand : hands)
    {
        for (const auto &g : gestures)
        {
            auto *item = new QListWidgetItem(
                QString("%1 - %2").arg(hand, g),
                gestureList_);

            item->setData(Qt::UserRole, g);
            item->setData(Qt::UserRole + 1, hand);
        }
    }

    if (gestureList_->count() > 0)
    {
        auto *first = gestureList_->item(0);
        gestureList_->setCurrentItem(first);

        const QString firstGesture = first->data(Qt::UserRole).toString();
        const QString firstHand = first->data(Qt::UserRole + 1).toString();
        gestureLabel_->setText(
            tr("Selected: %1 - %2").arg(firstHand, firstGesture));

        gestureBindings_[makeBindingKey("Right", "open_palm")] = "Move mouse (demo)";
        gestureBindings_[makeBindingKey("Right", "pinch")] = "Left click";
    }
}

void MainWindow::onGestureSelected(QListWidgetItem *item)
{
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    const QString hand = item->data(Qt::UserRole + 1).toString();

    gestureLabel_->setText(
        tr("Selected: %1 - %2").arg(hand, gestureName));

    const QString key = makeBindingKey(hand, gestureName);
    const QString currentAction = gestureBindings_.value(key, "None");

    int index = actionCombo_->findText(currentAction);
    if (index < 0)
        index = 0;
    actionCombo_->setCurrentIndex(index);
}

void MainWindow::onBindActionChanged(int index)
{
    auto *item = gestureList_->currentItem();
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    const QString hand = item->data(Qt::UserRole + 1).toString();
    const QString actionName = actionCombo_->itemText(index);

    applyBinding(hand, gestureName, actionName);
}

void MainWindow::applyBinding(const QString &hand,
                              const QString &gestureName,
                              const QString &actionName)
{
    const QString key = makeBindingKey(hand, gestureName);
    gestureBindings_[key] = actionName;

    statusLabel_->setText(
        tr("Bound %1 hand gesture '%2' to action '%3'")
            .arg(hand, gestureName, actionName));
}

void MainWindow::onTestActionClicked()
{
    auto *item = gestureList_->currentItem();
    if (!item)
        return;

    const QString gestureName = item->data(Qt::UserRole).toString();
    const QString hand = item->data(Qt::UserRole + 1).toString();
    const QString key = makeBindingKey(hand, gestureName);

    const QString actionName = gestureBindings_.value(key, "None");

    statusLabel_->setText(
        tr("Testing action '%1' for %2 hand gesture '%3'")
            .arg(actionName, hand, gestureName));

    if (actionName == "Left click")
        inputSim_->leftClick();
    else if (actionName == "Right click")
        inputSim_->rightClick();
    else if (actionName == "Double click")
        inputSim_->doubleClick();
    else if (actionName == "Scroll up")
        inputSim_->scroll(120);
    else if (actionName == "Scroll down")
        inputSim_->scroll(-120);
    else if (actionName == "Move mouse (demo)")
        inputSim_->moveRelative(50, 0);
}

void MainWindow::onTrackingToggled(bool checked)
{
    if (checked)
    {
        gestureEngine_->start();
        statusLabel_->setText(tr("Connecting to Python gesture server..."));
    }
    else
    {
        gestureEngine_->stop();
        statusLabel_->setText(tr("Tracking disabled"));
    }
}

// void MainWindow::onGestureDetected(const QString &gesture,
//                                    float x,
//                                    float y,
//                                    float z,
//                                    float angle,
//                                    const QString &handedness,
//                                    float confidence,
//                                    const QString &visible)
// {
//     Q_UNUSED(z);
//     Q_UNUSED(angle);

//     static float smoothX = -1.0f;
//     static float smoothY = -1.0f;

//     if (visible != "visible" || confidence < 0.4f)
//     {
//         smoothX = smoothY = -1.0f;
//         statusLabel_->setText(tr("Hand not visible or low confidence"));
//         return;
//     }

//     const QString key = makeBindingKey(handedness, gesture);
//     const QString action = gestureBindings_.value(key, "None");

//     static QString lastGestureLeft = "none";
//     static QString lastGestureRight = "none";

//     QString &lastGesture = (handedness == "Left") ? lastGestureLeft : lastGestureRight;

//     // One-shot click on fist transition
//     if (gesture != lastGesture)
//     {
//         if (gesture == "fist")
//         {
//             if (action == "Left click")
//                 inputSim_->leftClick();
//             else if (action == "Right click")
//                 inputSim_->rightClick();
//             else if (action == "Double click")
//                 inputSim_->doubleClick();

//             if (action != "None")
//             {
//                 statusLabel_->setText(
//                     tr("%1 hand fist → %2").arg(handedness, action));
//             }
//         }
//     }

//     // Pinch hold logic
//     if (gesture == "pinch" && lastGesture != "pinch")
//     {
//         if (action == "Left click")
//             inputSim_->mouseDown();
//         else if (action == "Right click")
//             inputSim_->mouseDownRight();

//         if (action != "None")
//         {
//             statusLabel_->setText(
//                 tr("%1 hand pinch → hold start (%2)")
//                     .arg(handedness, action));
//         }
//     }
//     else if (gesture != "pinch" && lastGesture == "pinch")
//     {
//         inputSim_->mouseUp();
//         statusLabel_->setText(
//             tr("%1 hand pinch released → mouseUp").arg(handedness));
//     }

//     lastGesture = gesture;

//     bool freezeCursor = (gesture == "pinch" || gesture == "fist");

//     if (action == "Move mouse (demo)" && !freezeCursor)
//     {
//         const float ALPHA = 0.25f;

//         QScreen *screen = QGuiApplication::primaryScreen();
//         if (!screen)
//             return;

//         QRect geom = screen->geometry();
//         float targetX = x * geom.width();
//         float targetY = y * geom.height();

//         if (smoothX < 0)
//             smoothX = targetX;
//         if (smoothY < 0)
//             smoothY = targetY;

//         smoothX = ALPHA * targetX + (1 - ALPHA) * smoothX;
//         smoothY = ALPHA * targetY + (1 - ALPHA) * smoothY;

//         inputSim_->moveAbsolute(static_cast<int>(smoothX),
//                                 static_cast<int>(smoothY));

//         statusLabel_->setText(
//             tr("Moving mouse (%1 hand) x=%2 y=%3")
//                 .arg(handedness)
//                 .arg(static_cast<int>(smoothX))
//                 .arg(static_cast<int>(smoothY)));
//     }
// }

void MainWindow::onConnectionStatusChanged(const QString &status)
{
    statusLabel_->setText(status);
}

void MainWindow::onHandsUpdated(const QVector<HandInfo> &hands)
{
    // --- Step 1: Create a map of current hands for easy lookup ---
    QMap<QString, HandInfo> currentHands;
    for (const auto &hand : hands)
    {
        if (hand.visible && hand.confidence > 0.5f)
        {
            currentHands[hand.handedness] = hand;
        }
    }

    // --- Step 2: Continuous Mouse Movement ---
    // Prioritize "Right" hand for mouse control, but fall back to any hand.
    const HandInfo *mouseHand = nullptr;
    if (currentHands.contains("Right"))
    {
        mouseHand = &currentHands["Right"];
    }
    else if (!currentHands.isEmpty())
    {
        mouseHand = &currentHands.first();
    }

    if (mouseHand)
    {
        // Absolute positioning with smoothing
        static QMap<QString, QPointF> smoothPos;
        const QString &handedness = mouseHand->handedness;

        if (!smoothPos.contains(handedness)) {
            smoothPos[handedness] = QPointF(mouseHand->wristX, mouseHand->wristY);
        }

        const float ALPHA = 0.3f;
        QPointF &sp = smoothPos[handedness];
        sp.setX(ALPHA * mouseHand->wristX + (1.0f - ALPHA) * sp.x());
        sp.setY(ALPHA * mouseHand->wristY + (1.0f - ALPHA) * sp.y());

        int screenWidth = QGuiApplication::primaryScreen()->geometry().width();
        int screenHeight = QGuiApplication::primaryScreen()->geometry().height();

        // Prevent mouse from being stuck at the edge if hand is lost and reacquired
        if (lastHands_.find(handedness) == lastHands_.end()) {
             sp = QPointF(mouseHand->wristX, mouseHand->wristY);
        }

        inputSim_->moveAbsolute(int(sp.x() * screenWidth), int(sp.y() * screenHeight));
    }


    // --- Step 3: Discrete Gesture Actions (Clicks, Scrolls) ---
    for (auto const &handedness : currentHands.keys())
    {
        const HandInfo &currentHand = currentHands[handedness];
        const HandInfo lastHand = lastHands_.value(handedness); // Default-constructed if not found

        const bool gestureJustStarted = (currentHand.gesture != "unknown" && currentHand.gesture != lastHand.gesture);

        if (gestureJustStarted)
        {
            const QString key = makeBindingKey(currentHand.handedness, currentHand.gesture);
            const QString action = gestureBindings_.value(key, "None");

            if (action == "Left click")
            {
                inputSim_->leftClick();
            }
            else if (action == "Right click")
            {
                inputSim_->rightClick();
            }
            else if (action == "Double click")
            {
                inputSim_->doubleClick();
            }
            else if (action == "Scroll up")
            {
                inputSim_->scroll(120); // One-shot scroll
            }
            else if (action == "Scroll down")
            {
                inputSim_->scroll(-120); // One-shot scroll
            }
        }
    }
    
    // --- Step 4: Update last known state for the next frame ---
    lastHands_ = currentHands;
}

void MainWindow::openSettingsDialog()
{
    SettingsDialog dlg(this);
    connect(&dlg, &SettingsDialog::configSaved, this, &MainWindow::onSettingsSaved);
    dlg.exec();
}

void MainWindow::onSettingsSaved()
{
    // Optionally show a brief status message
    statusLabel_->setText(tr("Settings saved; Python should pick them up automatically."));
}
